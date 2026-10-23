import json
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.config import settings
from app.core.logging import logger
from app.core.security import sanitize_relative_path
from app.core.errors import HackMateException
from app.services.gemini_client import gemini_client, GeminiOutputValidationError


# --- STAGE 1: REQUIREMENTS ANALYSIS SCHEMA ---
class RequirementsAnalysisSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    target_users: List[str] = Field(..., description="Identified primary user personas and audiences.")
    goals: List[str] = Field(..., description="High-level product and business objectives.")
    required_features: List[str] = Field(..., description="Concrete, user-facing and interactive features.")
    technical_constraints: List[str] = Field(..., description="Framework, styling, and architectural rules.")
    acceptance_criteria: List[str] = Field(..., description="Verifiable test and usability criteria.")
    clarifications_needed: Optional[List[str]] = Field(
        default=None,
        description="Questions for the user ONLY if essential details are genuinely ambiguous."
    )


# --- STAGE 2: SOLUTION PLANNING SCHEMA ---
class TaskItemSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., description="Unique task identifier, e.g. TASK-1")
    sequence_order: int = Field(..., description="Numeric order of execution")
    title: str = Field(..., description="Concise task title")
    description: str = Field(..., description="Step-by-step technical implementation instruction")
    dependencies: List[str] = Field(default_factory=list, description="IDs of tasks that must complete first")
    expected_files: List[str] = Field(..., description="Relative file paths this task generates or edits")
    completion_criteria: str = Field(..., description="Verifiable condition for task completion")


class ProjectPlanSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    framework: str = Field(default="react-vite", description="Target frontend framework: react-vite")
    summary: str = Field(..., description="Architectural summary of the proposed application")
    tasks: List[TaskItemSchema] = Field(..., description="Ordered list of development tasks")
    file_manifest: List[str] = Field(..., description="Complete list of all relative file paths required")


# --- STAGE 3: CODE GENERATION SCHEMA ---
class GeneratedFileSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    file_path: str = Field(..., description="Relative path from workspace root, e.g. 'src/App.tsx'")
    content: str = Field(..., description="Complete, unmodified, non-truncated source code")
    language: str = Field(..., description="Language identifier (typescript, json, html, css)")


class ProjectCodebaseSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    framework: str = "react-vite"
    files: List[GeneratedFileSchema] = Field(..., description="Complete list of all project files")


# --- STAGE 6: BOUNDED REPAIR SCHEMA ---
class CodeRepairSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    diagnosis: str = Field(..., description="Detailed explanation of the compilation or build failure")
    fixed_files: List[GeneratedFileSchema] = Field(..., description="List of corrected/patched files")


# Mandatory entry points for any functional React + Vite TypeScript project
MANDATORY_ENTRY_POINTS = {
    "package.json",
    "vite.config.ts",
    "index.html",
    "src/main.tsx",
    "src/App.tsx",
}


class AIService:
    """
    Manages the 6-stage Gemini AI engineering pipeline:
    1. Requirements Analysis
    2. Solution Planning
    3. Code Synthesis
    4. Codebase Validation
    5. Build & Test (delegated to RunnerService)
    6. Bounded Error Repair (at most 1 retry)
    """

    async def analyze_requirements(
        self,
        prompt: str,
        reference_url: Optional[str] = None,
        reference_guidance: Optional[str] = None
    ) -> RequirementsAnalysisSchema:
        """STAGE 1: Requirements Analysis via Gemini."""
        logger.info(f"Analyzing requirements for prompt: {prompt[:60]}...")

        system_instruction = (
            "You are a Principal Software Architect. Analyze the following user problem statement for a web application. "
            "Extract target users, product goals, required interactive features, technical constraints, and acceptance criteria. "
            "The target stack is strictly React 18+, TypeScript, Vite, and Tailwind CSS. "
            "Only suggest clarifications_needed if an essential requirement is genuinely ambiguous."
        )

        user_content = f"User Problem Statement:\n{prompt}"
        if reference_guidance:
            user_content += f"\n\n{reference_guidance}"
        elif reference_url:
            user_content += f"\n\nReference Website for design/layout cues:\n{reference_url}"

        return await gemini_client.generate_structured(
            prompt=user_content,
            system_instruction=system_instruction,
            schema=RequirementsAnalysisSchema,
            temperature=0.2,
        )

    async def generate_plan(self, prompt: str, analysis: RequirementsAnalysisSchema) -> ProjectPlanSchema:
        """STAGE 2: Architectural Solution Planning via Gemini."""
        logger.info("Generating structured solution plan and task DAG...")

        system_instruction = (
            "You are a Lead Software Architect. Based on the provided requirements analysis, "
            "generate a comprehensive, validated task plan and file manifest for a React + Vite + TypeScript application. "
            "Ensure tasks are ordered and include dependencies, expected files, and completion criteria. "
            "The file manifest MUST include package.json, vite.config.ts, index.html, src/main.tsx, src/App.tsx, and all component files."
        )

        user_content = (
            f"Original Prompt:\n{prompt}\n\n"
            f"Requirements Analysis:\n{analysis.model_dump_json(indent=2)}"
        )

        plan = await gemini_client.generate_structured(
            prompt=user_content,
            system_instruction=system_instruction,
            schema=ProjectPlanSchema,
            temperature=0.2,
        )

        # Validate that the manifest includes basic entry points
        manifest_set = set(plan.file_manifest)
        missing = MANDATORY_ENTRY_POINTS - manifest_set
        if missing:
            # Augment manifest with missing mandatory files
            plan.file_manifest.extend(list(missing))

        return plan

    async def generate_codebase(self, prompt: str, plan: ProjectPlanSchema) -> List[GeneratedFileSchema]:
        """STAGE 3: Complete React + Vite Codebase Synthesis."""
        logger.info(f"Synthesizing complete application codebase for {len(plan.file_manifest)} manifest files...")

        system_instruction = (
            "You are an Elite Frontend Engineer specializing in React 18, TypeScript, and Vite. "
            "Generate a complete, fully functional, production-ready website codebase that satisfies the provided plan. "
            "RULES:\n"
            "1. Output COMPLETE, compilable code for every file. Absolutely NO placeholder comments like '// TODO: implement later' or '// ... rest of code'.\n"
            "2. Ensure all imports match exactly between files.\n"
            "3. 'package.json' MUST include valid JSON with 'dependencies' (react, react-dom, lucide-react) and 'devDependencies' (@types/react, @types/react-dom, @vitejs/plugin-react, typescript, vite).\n"
            "4. Include all mandatory files: 'package.json', 'vite.config.ts', 'tsconfig.json', 'tsconfig.node.json', 'index.html', 'src/main.tsx', 'src/App.tsx', 'src/index.css'.\n"
            "5. Ensure all state and interactive features described in the user prompt actually function in the browser. For sound effects or audio alerts, use the browser's built-in Web Audio API (e.g. AudioContext oscillator) for reliable playback without external binary assets."
        )

        user_content = (
            f"Original Prompt:\n{prompt}\n\n"
            f"Approved Plan:\n{plan.model_dump_json(indent=2)}\n\n"
            f"Please generate the complete source code for all necessary files in the project."
        )

        codebase = await gemini_client.generate_structured(
            prompt=user_content,
            system_instruction=system_instruction,
            schema=ProjectCodebaseSchema,
            temperature=0.2,
            timeout_seconds=90.0,
        )

        # STAGE 4: Strict Validation
        validated_files = self.validate_codebase(codebase.files)
        return validated_files

    def validate_codebase(self, files: List[GeneratedFileSchema]) -> List[GeneratedFileSchema]:
        """
        STAGE 4: Strict Schema & Integrity Validation.
        Rejects missing required files, malformed responses, unsafe paths, and truncated output.
        Does NOT substitute a generic template.
        """
        if not files:
            raise GeminiOutputValidationError("Model returned zero generated files.")

        file_map: Dict[str, GeneratedFileSchema] = {}
        for gf in files:
            # 1. Path sanitization & traversal check
            clean_path = sanitize_relative_path(gf.file_path)
            gf.file_path = clean_path

            # 2. Check for empty or severely truncated content
            if not gf.content or len(gf.content.strip()) < 10:
                raise GeminiOutputValidationError(f"File '{clean_path}' contains truncated or empty content.")

            file_map[clean_path] = gf

        # 3. Check for mandatory entry points
        missing_entries = MANDATORY_ENTRY_POINTS - set(file_map.keys())
        if missing_entries:
            raise GeminiOutputValidationError(
                f"Generated codebase is missing mandatory entry points: {missing_entries}"
            )

        # 4. Validate package.json parses and has required scripts
        pkg_file = file_map.get("package.json")
        try:
            pkg_data = json.loads(pkg_file.content)
            scripts = pkg_data.get("scripts", {})
            if "build" not in scripts:
                raise GeminiOutputValidationError("package.json is missing required 'build' script.")
        except json.JSONDecodeError as e:
            raise GeminiOutputValidationError(f"Generated package.json is not valid JSON: {str(e)}")

        # 5. Check index.html points to src/main.tsx or valid entry point
        index_file = file_map.get("index.html")
        if "src/main.tsx" not in index_file.content and "src/main.jsx" not in index_file.content:
            logger.warning("index.html does not reference src/main.tsx explicitly; patching script tag.")
            if "</body>" in index_file.content:
                index_file.content = index_file.content.replace(
                    "</body>",
                    '  <script type="module" src="/src/main.tsx"></script>\n</body>'
                )

        # 6. Ensure tsconfig.json and tsconfig.node.json consistency
        if "tsconfig.json" not in file_map:
            file_map["tsconfig.json"] = GeneratedFileSchema(
                file_path="tsconfig.json",
                content=json.dumps({
                    "compilerOptions": {
                        "target": "ES2020",
                        "useDefineForClassFields": True,
                        "lib": ["ES2020", "DOM", "DOM.Iterable"],
                        "module": "ESNext",
                        "skipLibCheck": True,
                        "moduleResolution": "bundler",
                        "jsx": "react-jsx",
                        "strict": False
                    },
                    "include": ["src"]
                }, indent=2),
                language="json"
            )
        else:
            try:
                ts_data = json.loads(file_map["tsconfig.json"].content)
                refs = ts_data.get("references", [])
                needs_node_config = any("tsconfig.node.json" in r.get("path", "") for r in refs)
                if needs_node_config and "tsconfig.node.json" not in file_map:
                    file_map["tsconfig.node.json"] = GeneratedFileSchema(
                        file_path="tsconfig.node.json",
                        content=json.dumps({
                            "compilerOptions": {
                                "composite": True,
                                "skipLibCheck": True,
                                "module": "ESNext",
                                "moduleResolution": "bundler",
                                "allowSyntheticDefaultImports": True
                            },
                            "include": ["vite.config.ts"]
                        }, indent=2),
                        language="json"
                    )
            except Exception:
                pass

        return list(file_map.values())

    async def repair_codebase(
        self,
        prompt: str,
        files: List[GeneratedFileSchema],
        error_log: str,
        attempt: int
    ) -> List[GeneratedFileSchema]:
        """
        STAGE 6: Bounded Error Repair.
        Sends compiler error diagnostics and affected source files to Gemini for at most ONE automatic fix.
        """
        logger.info(f"Applying AI bounded repair via Gemini (attempt {attempt}/1)...")

        system_instruction = (
            "You are an Expert TypeScript & React Compiler Debugger. "
            "A build has failed inside a Node/Vite build environment. "
            "Analyze the compiler diagnostics, identify the syntax, type, or missing export errors, "
            "and output the corrected files. Return only the files that needed modification."
        )

        # Provide error log and relevant source files
        files_context = "\n\n".join([
            f"--- FILE: {f.file_path} ---\n{f.content}"
            for f in files
            if not f.file_path.endswith(".png") and not f.file_path.endswith(".ico")
        ])

        user_content = (
            f"Original Prompt: {prompt}\n\n"
            f"COMPILER ERROR LOG:\n{error_log[:4000]}\n\n"
            f"CURRENT SOURCE CODE:\n{files_context}"
        )

        repair_result = await gemini_client.generate_structured(
            prompt=user_content,
            system_instruction=system_instruction,
            schema=CodeRepairSchema,
            temperature=0.1,
        )

        # Merge fixed files into the original files list
        file_map = {f.file_path: f for f in files}
        for fixed in repair_result.fixed_files:
            clean_path = sanitize_relative_path(fixed.file_path)
            fixed.file_path = clean_path
            file_map[clean_path] = fixed
            logger.info(f"Applied repair patch to file: {clean_path}")

        return list(file_map.values())


ai_service = AIService()
