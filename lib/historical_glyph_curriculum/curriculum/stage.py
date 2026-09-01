"""Stage definitions for the curriculum."""
from dataclasses import dataclass
from typing import List, Tuple
from .difficulty import DifficultyConfig
from .concept import ConceptTemplate, make_concept

@dataclass
class StageDef:
    stage_id: int
    name: str
    description: str
    difficulty: DifficultyConfig
    concepts: List[ConceptTemplate]
    default_samples: int
    canvas_size: Tuple[int, int]
    seed_offset: int

    @property
    def stage_dir_name(self) -> str:
        return f'stage_{self.stage_id:02d}'

STAGES: List[StageDef] = []

# STAGE 1 - Clean Isolated Glyphs
bg_1 = ['paper', 'stone', 'stone', 'stone', 'paper', 'paper', (200, 190, 170), (80, 70, 60), 'sand', 'plaster', 'wood', 'metal']
concepts_1 = []
for i in range(12):
    mat = 'faded_white' if (i+1) in [2, 4, 6] else 'faded_black'
    concepts_1.append(make_concept(i+1, f'concept_{i+1}', background=bg_1[i], material=mat, rotation_deg=(-1.0, 1.0)))

STAGES.append(StageDef(
    stage_id=1, name='Clean Isolated Glyphs', description='',
    difficulty=DifficultyConfig(visibility=0.98, degradation=0.0, occlusion=0.0, geometric_variation=0.0, scene_complexity=0.05, resolution_quality=1.0, mixed_families=0.0, name='stage_01'),
    concepts=concepts_1, default_samples=2000, canvas_size=(512, 512), seed_offset=10000
))

# STAGE 2 - Material Variation
materials_2 = ['faded_black', 'faded_white', 'ink', 'paint', 'carved']
bg_2 = ['paper', 'stone', 'wood', 'sand', 'metal']
concepts_2 = [make_concept(i+1, f'concept_{i+1}', material=materials_2[i%5], background=bg_2[i%5], rotation_deg=(-3.0, 3.0)) for i in range(12)]
STAGES.append(StageDef(
    stage_id=2, name='Material Variation', description='',
    difficulty=DifficultyConfig(visibility=0.92, degradation=0.05, occlusion=0.0, geometric_variation=0.05, scene_complexity=0.05, resolution_quality=0.97, mixed_families=0.0, name='stage_02'),
    concepts=concepts_2, default_samples=2500, canvas_size=(512, 512), seed_offset=20000
))

# STAGE 3 - Controlled Degradation
blur_vals = [0.8, 1.5, 0.8, 1.5, 0.8, 1.5, 0.8, 1.5, 1.0, 1.2, 1.0, 1.2]
ero_vals = [1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2]
res_vals = [0.75, 0.5, 0.75, 0.5, 0.75, 0.5, 0.75, 0.5, 0.6, 0.6, 0.6, 0.6]
fade_vals = [0.15, 0.30, 0.15, 0.30, 0.15, 0.30, 0.15, 0.30, 0.2, 0.2, 0.2, 0.2]
concepts_3 = [make_concept(i+1, f'concept_{i+1}', blur_sigma=blur_vals[i], erosion_iters=ero_vals[i], resolution_scale=res_vals[i], fading_alpha=fade_vals[i], jpeg_quality=50) for i in range(12)]
STAGES.append(StageDef(
    stage_id=3, name='Controlled Degradation', description='',
    difficulty=DifficultyConfig(visibility=0.78, degradation=0.35, occlusion=0.0, geometric_variation=0.1, scene_complexity=0.05, resolution_quality=0.85, mixed_families=0.0, name='stage_03'),
    concepts=concepts_3, default_samples=3000, canvas_size=(512, 512), seed_offset=30000
))

# STAGE 4 - Discriminative-Aware Occlusion
occ_levels = ['mild', 'moderate', 'severe']
concepts_4 = [make_concept(i+1, f'concept_{i+1}', occlusion=occ_levels[i%3], protect_discriminative=(i%2==0), blur_sigma=1.0) for i in range(12)]
STAGES.append(StageDef(
    stage_id=4, name='Discriminative-Aware Occlusion', description='',
    difficulty=DifficultyConfig(visibility=0.65, degradation=0.30, occlusion=0.45, geometric_variation=0.1, scene_complexity=0.05, resolution_quality=0.85, mixed_families=0.0, name='stage_04'),
    concepts=concepts_4, default_samples=3000, canvas_size=(512, 512), seed_offset=40000
))

# STAGE 5 - Geometric Variation
rot_vals = [(-8,8), (-18,18), (-35,35), (-8,8), (-18,18), (-35,35), (-8,8), (-18,18), (-35,35), (-8,8), (-18,18), (-35,35)]
skew_vals = [0.05, 0.10, 0.15, 0.05, 0.10, 0.15, 0.05, 0.10, 0.15, 0.05, 0.10, 0.15]
concepts_5 = [make_concept(i+1, f'concept_{i+1}', rotation_deg=rot_vals[i], perspective=True, perspective_skew=skew_vals[i]) for i in range(12)]
STAGES.append(StageDef(
    stage_id=5, name='Geometric Variation', description='',
    difficulty=DifficultyConfig(visibility=0.72, degradation=0.25, occlusion=0.15, geometric_variation=0.70, scene_complexity=0.05, resolution_quality=0.85, mixed_families=0.0, name='stage_05'),
    concepts=concepts_5, default_samples=3000, canvas_size=(512, 512), seed_offset=50000
))

# STAGE 6 - Multiple Glyphs
concepts_6 = [make_concept(i+1, f'concept_{i+1}', glyphs_per_image=[2,3,4][i%3], mixed_families=(i%2!=0), material=materials_2[i%5]) for i in range(12)]
STAGES.append(StageDef(
    stage_id=6, name='Multiple Glyphs', description='',
    difficulty=DifficultyConfig(visibility=0.75, degradation=0.25, occlusion=0.1, geometric_variation=0.30, scene_complexity=0.35, resolution_quality=0.88, mixed_families=0.15, name='stage_06'),
    concepts=concepts_6, default_samples=3000, canvas_size=(768, 512), seed_offset=60000
))

# STAGE 7 - Glyph Groups
concepts_7 = [make_concept(i+1, f'concept_{i+1}', glyphs_per_image=[3,4,5,6][i%4], spacing_px=[10,15,20][i%3]) for i in range(12)]
STAGES.append(StageDef(
    stage_id=7, name='Glyph Groups', description='',
    difficulty=DifficultyConfig(visibility=0.70, degradation=0.30, occlusion=0.15, geometric_variation=0.35, scene_complexity=0.50, resolution_quality=0.85, mixed_families=0.25, name='stage_07'),
    concepts=concepts_7, default_samples=3000, canvas_size=(1024, 384), seed_offset=70000
))

# STAGE 8 - Text Lines
concepts_8 = [make_concept(i+1, f'concept_{i+1}', glyphs_per_image=[5,6,7,8,9,10][i%6], baseline_drift_px=[0,5,10][i%3], blur_sigma=0.5) for i in range(12)]
STAGES.append(StageDef(
    stage_id=8, name='Text Lines', description='',
    difficulty=DifficultyConfig(visibility=0.65, degradation=0.40, occlusion=0.20, geometric_variation=0.45, scene_complexity=0.65, resolution_quality=0.80, mixed_families=0.30, name='stage_08'),
    concepts=concepts_8, default_samples=2500, canvas_size=(1024, 256), seed_offset=80000
))

# STAGE 9 - Multi-Line Text
concepts_9 = [make_concept(i+1, f'concept_{i+1}', glyphs_per_image=(5,6), canvas_size=(1024,768), baseline_drift_px=[2,5,8][i%3]) for i in range(12)]
STAGES.append(StageDef(
    stage_id=9, name='Multi-Line Text', description='',
    difficulty=DifficultyConfig(visibility=0.58, degradation=0.50, occlusion=0.25, geometric_variation=0.55, scene_complexity=0.75, resolution_quality=0.75, mixed_families=0.35, name='stage_09'),
    concepts=concepts_9, default_samples=2000, canvas_size=(1024, 768), seed_offset=90000
))

# STAGE 10 - Document Structure
concepts_10 = [make_concept(i+1, f'concept_{i+1}', background='aged_document', canvas_size=(1024,1024)) for i in range(12)]
STAGES.append(StageDef(
    stage_id=10, name='Document Structure', description='',
    difficulty=DifficultyConfig(visibility=0.52, degradation=0.55, occlusion=0.30, geometric_variation=0.60, scene_complexity=0.80, resolution_quality=0.72, mixed_families=0.40, name='stage_10'),
    concepts=concepts_10, default_samples=1500, canvas_size=(1024, 1024), seed_offset=100000
))

# STAGE 11 - Severe Historical Degradation
concepts_11 = [make_concept(i+1, f'concept_{i+1}', blur_sigma=3.0, erosion_iters=3, fading_alpha=0.55, resolution_scale=0.30, jpeg_quality=20, occlusion='severe', protect_discriminative=True) for i in range(12)]
STAGES.append(StageDef(
    stage_id=11, name='Severe Historical Degradation', description='',
    difficulty=DifficultyConfig(visibility=0.38, degradation=0.82, occlusion=0.50, geometric_variation=0.75, scene_complexity=0.75, resolution_quality=0.55, mixed_families=0.35, name='stage_11'),
    concepts=concepts_11, default_samples=1500, canvas_size=(1024, 768), seed_offset=110000
))

# STAGE 12 - Realistic Mixed Historical Scenes
bg_12 = ['inscription', 'manuscript', 'stone_relief', 'damaged', 'glass_scene']
concepts_12 = [make_concept(i+1, f'concept_{i+1}', background=bg_12[i%5], mixed_families=True) for i in range(12)]
STAGES.append(StageDef(
    stage_id=12, name='Realistic Mixed Historical Scenes', description='',
    difficulty=DifficultyConfig(visibility=0.45, degradation=0.70, occlusion=0.40, geometric_variation=0.80, scene_complexity=0.90, resolution_quality=0.60, mixed_families=0.50, name='stage_12'),
    concepts=concepts_12, default_samples=1500, canvas_size=(1024, 1024), seed_offset=120000
))

def get_stage(stage_id: int) -> StageDef:
    """Get a stage definition by its ID."""
    for stage in STAGES:
        if stage.stage_id == stage_id:
            return stage
    raise ValueError(f"Stage {stage_id} not found.")
