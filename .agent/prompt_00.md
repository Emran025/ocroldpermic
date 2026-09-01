# Professional Specification Prompt — Universal Historical Glyph Synthetic Rendering & Augmentation Studio

## Role

You are a senior computer-vision engineer, graphics/rendering engineer, OCR researcher, and Python library architect.

Your task is to design and implement a **production-quality, modular, extensible, and testable Python library** for generating synthetic images of historical writing systems and ancient manuscripts.

The system will ultimately be used to generate training data for object-detection and OCR models, especially YOLO-based character detection systems, where real annotated manuscript data is scarce.

Do not merely provide a prototype or a collection of scripts. Build this as a **proper reusable Python module/package** with clean architecture, strong abstractions, deterministic behavior when requested, validation, testing, documentation, and a public API.

The implementation details are yours to determine. You should make technically sound architectural decisions rather than blindly following the examples below.

---

# 1. Core Objective

The fundamental objective is to generate realistic synthetic representations of historical glyphs from SVG source artwork and render them onto arbitrary backgrounds while simulating the physical and visual conditions under which ancient inscriptions, manuscripts, marks, symbols, or degraded writing may appear.

The system must support phenomena such as:

* engraved/carved characters
* raised/embossed characters
* faded black marks
* faded white marks
* transparent/glass-like marks
* subtle burned or pigmented marks
* partially degraded characters
* partially occluded characters
* blurred or low-contrast characters
* perspective distortion
* geometric deformation
* irregular historical-looking surfaces
* texture interaction
* lighting variation
* material-dependent appearance
* character rotation
* combinations of multiple glyphs
* glyphs originating from multiple visual variants of the same writing system

The library should be **general-purpose**.

It must not contain Old Permic-specific assumptions in its architecture.

Old Permic may be one dataset using the library, but the library itself should be capable of handling completely different historical scripts and writing systems.

---

# 2. SVG Is the Authoritative Glyph Source

This is a critical architectural requirement.

The system must **NOT depend on a font file for glyph generation**.

The actual glyph source is a collection of SVG files.

A Unicode character code is only an identifier used to locate the corresponding SVG.

For example:

```text
U+10350.svg
U+10351.svg
U+10352.svg
```

The system receives a Unicode character such as:

```python
"\U00010350"
```

and resolves the corresponding SVG artwork from the configured glyph library.

The SVG itself is the authoritative visual representation.

Do not render the glyph using:

```python
ImageFont.truetype(...)
draw.text(...)
```

for the primary generation pipeline.

Instead:

```text
Unicode Character
        ↓
Glyph Resolver
        ↓
SVG File
        ↓
SVG Parser / Rasterizer
        ↓
Normalized Glyph Representation
        ↓
Rendering Pipeline
```

The architecture should allow multiple SVG rendering technologies if appropriate, but the public API should hide those implementation details.

---

# 3. Glyph Library Structure

The library must support multiple visual families / source sets.

A conceptual structure may look like:

```text
fonts/
│
├── variant_a/
│   ├── regular/
│   │   ├── U+10350.svg
│   │   ├── U+10351.svg
│   │   └── ...
│   │
│   ├── bold/
│   │   ├── U+10350.svg
│   │   └── ...
│   │
│   └── italic/
│       ├── U+10350.svg
│       └── ...
│
├── variant_b/
│   ├── regular/
│   ├── bold/
│   └── italic/
│
└── variant_c/
    ├── regular/
    └── bold/
```

However, do not hard-code this exact number of levels.

The system should support:

* one family
* several families
* several styles
* multiple versions of the same style
* arbitrary nesting where reasonable
* future expansion without modifying the core renderer

The library must be able to discover and index available SVG glyphs.

A glyph should have metadata conceptually similar to:

```text
Unicode
Code point
Family
Variant
Style
Source path
SVG dimensions
Bounding box
Normalized mask
Optional metadata
```

Do not assume that all families contain the same Unicode characters.

The system must validate missing glyphs gracefully.

---

# 4. Unicode-Based Glyph Resolution

The public API should allow something conceptually similar to:

```python
renderer.render(
    char="\U00010350"
)
```

The system should resolve:

```text
Unicode
    ↓
available glyph variants
    ↓
SVG source
```

The caller must also be able to explicitly select:

```python
family=...
variant=...
style=...
```

or allow the system to select them automatically.

The system should support:

```text
single source selection
random source selection
weighted source selection
mixed-source rendering
```

For example, a generated image may contain:

```text
Glyph 1 → family A
Glyph 2 → family B
Glyph 3 → family A
Glyph 4 → family C
```

This must be intentional and configurable.

---

# 5. Rendering API

Design a clean public API.

Conceptually, the library should allow calls such as:

```python
image = renderer.render(
    char="\U00010350",
    background=background,
    operation="engraved"
)
```

But the architecture should be richer than this example.

The renderer should accept:

### Character

```text
Unicode character
```

### Background

Either:

```text
RGB/RGBA color
```

or:

```text
image
```

The caller must be able to provide:

```python
background=(120, 110, 90)
```

or:

```python
background="stone.jpg"
```

or a PIL image / NumPy array where appropriate.

The renderer should not assume that the background is a synthetic texture.

External real-world photographs must be supported.

---

# 6. Material / Operation System

The system must provide a strongly typed or validated operation/material abstraction.

At minimum support:

```text
engraved
raised
faded_black
faded_white
glass
random
```

Do not implement these merely as unrelated functions.

Create a coherent material/rendering architecture so additional materials can later be added without modifying the core engine.

Examples of future materials:

```text
ink
charcoal
pigment
paint
scratched
etched
burned
frosted
chalk
metallic
oxidized
weathered
```

The public API should make the operation fully controllable.

---

# 7. Engraved Rendering

The engraved mode must simulate a character physically carved into the surface.

Do not simply draw the glyph in dark color.

The glyph should generate a depth/height field.

Conceptually:

```text
SVG Mask
    ↓
Distance Transform
    ↓
Depth Profile
    ↓
Surface Normals
    ↓
Lighting
    ↓
Cavity Shadow
    ↓
Surface Interaction
```

The interior of the glyph must participate in the effect.

The system must support configurable:

```text
depth
edge sharpness
cavity profile
surface roughness
shadow strength
highlight strength
lighting direction
lighting softness
irregularity
erosion
```

The result should resemble a carved or engraved mark rather than a flat black glyph.

---

# 8. Raised / Embossed Rendering

The raised operation should use a positive height field.

The glyph should behave as though it protrudes from the surface.

It should support:

```text
height
edge softness
lighting
shadow
surface interaction
irregularity
```

The system should use the same underlying geometry/depth abstractions as engraving where appropriate.

Avoid duplicated rendering logic.

---

# 9. Faded / Burned / Pigmented Marks

The system must support subtle flat marks where the glyph is present across its full shape but has very low contrast against the background.

Examples:

```text
faded_black
faded_white
```

The glyph should NOT become an outline.

The full interior of the glyph must be represented.

The caller should be able to control:

```text
opacity
blur
density
color
irregularity
local fading
texture interaction
```

Opacity should support very subtle values so that generated examples range from:

```text
clearly visible
        ↓
faint
        ↓
very faint
        ↓
barely visible
```

The system should optionally generate nonuniform pigment/burn density.

---

# 10. Glass / Transparent Glyph Rendering

The glass mode must not be implemented as an outline-only effect.

The complete glyph shape must behave as a transparent material.

The background should remain visible through the glyph, but the glyph should alter the visual appearance through effects such as:

```text
refraction
subtle displacement
internal optical variation
transparency
surface thickness
Fresnel-like reflection
soft highlights
edge reflection
```

The interior of the glyph must contribute to the effect.

A completely flat background may naturally produce weak refraction, but the renderer must still behave correctly.

Do not rely exclusively on gradients at the glyph boundary.

The implementation should conceptually model:

```text
Background
      ↓
Transparent Glyph Volume
      ↓
Optical Transformation
      ↓
Subtle Reflection / Refraction
      ↓
Final Surface
```

The glass material must expose configurable parameters.

---

# 11. Discriminative Region Analysis

This is one of the most important research components.

The system must analyze the available glyph set and determine which regions of each glyph are:

1. common/shared across multiple characters
2. moderately distinctive
3. highly distinctive
4. critical for distinguishing one character from another

The purpose is not merely visualization.

The resulting analysis will be used by the occlusion/degradation system.

For each character, construct a **discriminative map**.

Conceptually:

```text
Glyph
 ↓
Compare against other glyphs
 ↓
Local structural analysis
 ↓
Similarity / difference analysis
 ↓
Discriminative score map
 ↓
Critical regions
```

Do not simply compare raw pixels if that would make the analysis fragile.

Consider suitable representations such as:

```text
normalized masks
distance transforms
skeletons
local shape descriptors
connected components
stroke structure
regional similarity
```

Choose an appropriate method and explain your architectural decision in the documentation.

The output should conceptually contain:

```text
score map
critical regions
important regions
common regions
```

---

# 12. Critical Requirement for Occlusion

The occlusion system must use the discriminative analysis.

Randomly hiding arbitrary portions of a glyph is NOT sufficient.

The generator must prevent catastrophic removal of all highly discriminative regions.

For example:

```text
Original Glyph
████████████
██      ████
██  ████████
██      ████
████████████
```

If a specific region uniquely identifies the character, the occlusion system should normally preserve at least one sufficient discriminative region.

The generated character may therefore be heavily degraded:

```text
░░░░░░████
░░    ████
░░  ██████
██      ██
████░░░░░░
```

but the remaining visible information should still contain meaningful class-specific evidence.

The exact algorithm is your responsibility.

Do not hard-code simplistic rectangles if a better shape-aware method can be implemented.

---

# 13. Occlusion Levels

Support configurable degradation levels such as:

```text
mild
moderate
severe
extreme
```

or an equivalent continuous parameter.

The system should control:

```text
percentage hidden
number of hidden regions
region size
shape of occlusion
blur
fading
erosion
local transparency
```

Critically:

```text
Occlusion must be aware of discriminative regions.
```

The system should be able to guarantee or probabilistically enforce:

```text
at least one important discriminative region remains visible
```

unless the caller explicitly requests unrestricted corruption.

---

# 14. Regional Blurring and Partial Visibility

The system must support degradation beyond binary hiding.

For example:

```text
fully visible
partially transparent
blurred
low contrast
locally erased
textured over
scratched
weathered
```

A region can therefore be degraded without being completely removed.

The occlusion system should be composable.

For example:

```text
engraved
+
surface erosion
+
partial occlusion
+
blur
+
low contrast
```

should be possible.

---

# 15. Multi-Glyph Composition

The library must eventually support generating images containing multiple glyphs.

For example:

```python
renderer.render_sequence(
    chars=[...]
)
```

or an equivalent API.

Support:

```text
single glyph
multiple glyphs
random glyph selection
mixed glyph families
same family
mixed styles
```

Different glyphs in one image may originate from different SVG source families.

This must be configurable.

---

# 16. Rotation

Support controlled rotation.

Rotation should be configurable and optionally randomized.

A requested use case is:

```text
random rotation ∈ [-18°, +18°]
```

Do not introduce rotation artifacts unnecessarily.

Rotation should preserve:

```text
mask
geometry
annotation
```

correctly.

---

# 17. Geometric / Perspective Studio

The system should include a dedicated transformation layer that can make glyphs appear photographed from a non-perfect angle.

This should go beyond simple rotation.

Potential transformations include:

```text
affine transformation
perspective transformation
shear
anisotropic scaling
nonuniform scaling
local warping
keystone distortion
surface curvature
```

Examples:

```text
left side slightly compressed
right side slightly expanded

top slightly compressed
bottom unchanged

one side shortened without uniformly scaling the entire glyph

local deformation around individual strokes
```

The important requirement is that transformations should be **controlled and physically/plausibly motivated**, rather than arbitrary distortion.

The goal is to simulate the appearance of a historical glyph photographed on a surface at an angle.

---

# 17-A. Resolution and Image Quality Degradation

The Studio must support controlled degradation of the final image resolution and visual quality.

This is important because historical manuscript and inscription images may originate from:

* low-resolution scans
* old photographs
* compressed images
* camera captures
* screenshots
* heavily resized historical documents
* distant or oblique photographs

Resolution degradation must be applied primarily as a **final-stage image degradation process**, after glyph rendering, composition, geometric transformation, material simulation, and annotation geometry have been established.

Support operations such as:

```text
downscaling
upscaling after downscaling
controlled interpolation
pixelation
softening
low-resolution simulation
JPEG-like compression artifacts
quantization
sensor-like noise
slight sharpening after degradation
```

The system should allow a target resolution or degradation factor to be specified.

For example:

```python
resolution_scale=1.0
resolution_scale=0.75
resolution_scale=0.50
resolution_scale=0.25
```

or an equivalent abstraction.

The implementation must distinguish between:

```text
logical/render resolution
```

and:

```text
final output resolution
```

so that geometric annotations remain correct.

The degradation pipeline should support both deterministic and randomized behavior.

Example conceptual pipeline:

```text
SVG
 ↓
High-resolution glyph representation
 ↓
Material rendering
 ↓
Composition
 ↓
Geometry / perspective
 ↓
Occlusion / degradation
 ↓
Final-resolution degradation
 ↓
Noise / compression / optical degradation
 ↓
Export
```

The purpose is to simulate realistic image acquisition conditions rather than simply making the image smaller.

The implementation should avoid unnecessarily destroying the discriminative structure unless a severe degradation level is explicitly requested.


# 18. Surface-Aware Distortion

Where possible, distinguish between:

```text
glyph geometry
```

and:

```text
surface geometry
```

The same glyph should be capable of being rendered onto:

```text
flat stone
rough stone
curved stone
wood
wall
paper
metal
other surfaces
```

The architecture should make it possible to introduce surface-dependent distortion later.

---

# 19. Background System

The renderer must support:

### Solid backgrounds

```python
background=(r, g, b)
```

### External images

```python
background="wall.jpg"
```

### PIL images

### NumPy arrays

### Synthetic textures

Provide a background abstraction so additional procedural materials can be added later.

Potential procedural surfaces:

```text
stone
wall
paper
wood
metal
sand
plaster
```

Do not make the renderer dependent on any one background type.

---

# 20. Color Control

The caller must be able to explicitly provide the glyph/material color where applicable.

For example:

```python
color=(0, 0, 0)
```

or:

```python
color=(255, 255, 255)
```

For materials such as engraving or glass where a simple color may not be physically appropriate, the parameter may be ignored or interpreted appropriately.

The API should remain coherent.

---

# 21. Randomization Architecture

Randomization must be centralized and controllable.

The caller should be able to specify:

```textseed
```

so that:

```textsame seed → same result
```

when deterministic behavior is requested.

Randomization should cover:

```textglyph source
material
rotation
opacity
depth
lighting
texture
degradation
occlusion
distortion
surface variation
```

The system should avoid hidden calls to global random state wherever possible.

Use an explicit RNG abstraction.

---

# 22. Reproducibility

Every generated sample should optionally be reproducible.

Ideally the renderer should support a generation configuration such as:

```textseed
character
source glyph
operation
parameters
background
transformations
```

and optionally return metadata describing how the image was generated.

This is important for research reproducibility.

---

# 23. YOLO Annotation Support

The library must preserve the transformed glyph geometry and provide correct object annotations.

The final visible glyph and its transformations must be reflected in the annotation.

Support at minimum:

```textYOLO bounding box
```

Preferably design the geometry layer so that future support for:

```textpolygon
segmentation mask
instance mask
```

is possible.

The mask used for annotations must remain independent from visual effects such as:

```textlighting
shadow
refraction
texture
color
```

unless explicitly configured otherwise.

---

# 24. Separation of Concerns

The architecture should clearly separate:

```textGlyph discovery
SVG loading
SVG rasterization
Normalization
Geometry
Materials
Backgrounds
Lighting
Distortion
Degradation
Discriminative analysis
Occlusion
Composition
Annotation
Export
Configuration
```

Do not create one giant renderer class.

Use composable components.

A conceptual architecture could resemble:

```text
GlyphRepository
        ↓
GlyphResolver
        ↓
GlyphRasterizer
        ↓
GlyphGeometry
        ↓
TransformationPipeline
        ↓
MaterialPipeline
        ↓
DegradationPipeline
        ↓
CompositionPipeline
        ↓
AnnotationGenerator
        ↓
Exporter
```

You may improve this architecture if you identify a better design.

---

# 25. Suggested Package Structure

A possible structure is:

```text
historical_glyph_studio/
│
├── __init__.py
│
├── config/
│   ├── models.py
│   └── validation.py
│
├── glyphs/
│   ├── repository.py
│   ├── resolver.py
│   ├── svg_loader.py
│   ├── rasterizer.py
│   └── normalization.py
│
├── geometry/
│   ├── transforms.py
│   ├── perspective.py
│   ├── deformation.py
│   └── distance.py
│
├── materials/
│   ├── base.py
│   ├── engraved.py
│   ├── raised.py
│   ├── faded.py
│   └── glass.py
│
├── surfaces/
│   ├── base.py
│   ├── procedural.py
│   └── image.py
│
├── analysis/
│   ├── discriminative.py
│   ├── skeleton.py
│   └── regions.py
│
├── degradation/
│   ├── occlusion.py
│   ├── blur.py
│   ├── erosion.py
│   └── fading.py
│
├── composition/
│   └── composer.py
│
├── annotation/
│   └── yolo.py
│
├── rendering/
│   └── pipeline.py
│
├── export/
│   └── image.py
│
└── tests/
```

This is only a conceptual starting point. You are responsible for choosing the final structure.

---

# 26. Public API

The final library should expose a clean high-level interface.

For example:

```python
from historical_glyph_studio import GlyphStudio

studio = GlyphStudio(
    glyph_root="fonts/"
)

result = studio.render(
    char="\U00010350",
    background="stone.jpg",
    operation="engraved",
    rotation=(-18, 18),
    occlusion=True
)
```

The exact API is yours to design.

It should be intuitive enough that a researcher can use the library without understanding its internal rendering implementation.

---

# 27. Batch Generation

Provide an API for dataset generation.

Conceptually:

```python
studio.generate_dataset(
    chars=[...],
    count=10000,
    output_dir="dataset/"
)
```

Support:

```textsingle character
random character
balanced character distribution
weighted character distribution
multiple glyphs per image
mixed source families
mixed materials
random backgrounds
random transformations
random degradation
```

The system should avoid class imbalance when a balanced mode is requested.

---

# 28. Metadata

Every generated image should optionally have metadata.

For example:

```json
{
  "character": "U+10350",
  "source_family": "...",
  "source_style": "...",
  "operation": "engraved",
  "rotation": 7.4,
  "occlusion_level": 0.35,
  "seed": 123456,
  "bbox": [...]
}
```

Do not force metadata generation when disabled.

---

# 29. Validation

The library must validate:

```textinvalid Unicode
missing SVG
malformed SVG
unsupported image format
invalid operation
invalid parameter ranges
invalid background
empty glyph
degenerate SVG
```

Errors should be clear and actionable.

---

# 30. Testing Requirements

Do not consider the implementation complete until it has tests.

At minimum test:

```textSVG discovery
Unicode resolution
multiple families
multiple styles
missing glyphs
SVG rasterization
mask generation
normalization
engraving
raised rendering
faded rendering
glass rendering
rotation
perspective
occlusion
discriminative maps
YOLO bounding boxes
random seed reproducibility
batch generation
```

Include regression tests for important rendering behaviors.

The glass renderer must have a test proving that the **interior of the glyph contributes to the effect**, not merely its outline.

The engraving renderer must have a test proving that the glyph creates an actual depth-dependent internal variation.

---

# 31. Visual Verification

Because this is a computer-vision/rendering project, automated tests alone are insufficient.

Create a small demonstration/test suite that generates visual examples for:

```textengraved
raised
faded_black
faded_white
glass
occluded
perspective distorted
multi-glyph
mixed-source
```

Also generate visualization of the discriminative maps.

The developer/AI implementing this should inspect the generated results and correct obvious rendering failures.

Do not stop after successfully executing Python code.

The objective is **visually meaningful output**, not merely syntactically correct code.

---

# 32. Research-Oriented Design

The system is intended for synthetic-to-real OCR research.

Therefore prioritize:

```textreproducibility
controllability
parameterization
traceability
extensibility
```

Avoid black-box behavior that cannot be reproduced.

Every major transformation should be controllable and preferably represented in a configuration object.

---

# 33. Important Design Principle — SVG First, Font Optional

Do not introduce a dependency on a font as the canonical glyph representation.

The system must work even if:

```textthere is no TTF/OTF font at all.
```

A font may optionally be supported in the future as another glyph source, but SVG must remain a first-class and fully supported source.

This is essential because historical visual forms may differ substantially from modern Unicode font glyphs.

The Unicode code point identifies the character; the SVG defines its actual visual form.

---

# 34. Important Design Principle — Visual Variants Matter

Do not assume that one Unicode character has one visual form.

The same Unicode character may have:

```textvariant A
variant B
variant C
bold version
italic version
historical version
regional version
```

The architecture must treat these as legitimate alternative visual realizations.

The generator should be able to:

```textselect one family
select one style
randomly select among families
mix families within one image
```

according to configuration.

---

# 35. Important Design Principle — Synthetic Data Must Be Hard but Informative

The purpose of degradation is not to destroy the character.

The purpose is to force the detector to learn robust structural evidence.

Therefore:

```textbad augmentation:
hide the only discriminative region

good augmentation:
hide common regions while preserving enough distinctive structure
```

The system should explicitly encode this principle.

When possible, quantify how much discriminative information remains after degradation.

---

# 36. Studio-Level Extensibility

Think of the library as a **Historical Glyph Simulation Studio**, not merely a text renderer.

Future modules may include:

```textsurface cracks
erosion
weathering
camera blur
motion blur
lens distortion
lighting direction
shadow
dust
scratches
partial coverage
stone curvature
photographic perspective
color aging
fading
noise
compression artifacts
```

The current architecture should make adding these effects possible without rewriting the core.

---

# 37. Implementation Strategy

You are responsible for implementing the complete system.

Do not simply explain how it could be implemented.

Work through the following phases:

### Phase 1

Inspect the requirements and design the architecture.

### Phase 2

Implement the glyph repository and SVG resolver.

### Phase 3

Implement SVG rasterization and normalization.

### Phase 4

Implement the common geometry representation.

### Phase 5

Implement the material/rendering system.

### Phase 6

Implement discriminative-region analysis.

### Phase 7

Implement discriminative-aware occlusion and degradation.

### Phase 8

Implement geometric/perspective transformations.

### Phase 9

Implement multi-glyph composition.

### Phase 10

Implement YOLO annotation generation.

### Phase 11

Implement batch dataset generation.

### Phase 12

Implement tests and visual demonstrations.

### Phase 13

Run the complete test suite.

### Phase 14

Generate representative images and inspect them.

### Phase 15

Fix rendering or architectural problems discovered during testing.

Do not declare completion simply because the code runs.

---

# 38. Engineering Quality

The implementation must prioritize:

```textclear typing
clean interfaces
small cohesive classes/functions
low coupling
high cohesion
testability
documentation
validation
deterministic randomization
performance
```

Avoid:

```textmonolithic classes
global mutable state
hard-coded paths
hard-coded Unicode ranges
hard-coded number of fonts
font-dependent glyph rendering
magic constants without explanation
duplicated rendering algorithms
```

Use modern Python practices where appropriate.

---

# 39. Performance

The system may eventually generate hundreds of thousands or millions of synthetic samples.

Therefore consider:

```textcaching
precomputed glyph masks
cached discriminative maps
lazy loading
efficient NumPy operations
avoiding repeated SVG parsing
parallel batch generation where safe
```

Discriminative analysis should preferably be performed once per glyph set and cached rather than recomputed for every generated image.

---

# 40. Final Acceptance Criteria

The implementation is considered successful only when all of the following are true:

1. The library can discover SVG glyphs from configurable directories.

2. Unicode characters can resolve to SVG files.

3. Multiple glyph families/styles are supported.

4. The same Unicode character can have multiple visual variants.

5. No font file is required for glyph rendering.

6. Backgrounds can be solid colors or real images.

7. Engraving produces an actual depth-like visual effect.

8. Raised rendering produces a positive surface effect.

9. Faded black/white rendering uses the full glyph, not only its outline.

10. Glass rendering affects the interior of the glyph and does not reduce to an outline.

11. Glyphs can be rotated within configurable limits such as ±18°.

12. Perspective and nonuniform deformation are supported.

13. Multiple glyphs can be composed into one image.

14. Different glyphs may originate from different SVG families when configured.

15. Discriminative regions can be analyzed automatically.

16. Occlusion can use discriminative information.

17. Critical regions can be protected from complete destruction.

18. Partial blur/fading/erosion can be applied.

19. YOLO bounding boxes remain correct after transformations.

20. Generation is reproducible using explicit seeds.

21. Batch generation is supported.

22. Metadata can optionally describe each generated sample.

23. Automated tests exist.

24. Visual demonstration outputs exist.

25. The code is organized as a reusable library rather than a one-off notebook script.

---

# 41. Final Instruction

Take ownership of the engineering decisions.

Do not ask me to manually implement individual components that you can reasonably design and implement yourself.

Do not simplify the architecture merely to make the first version shorter.

At the same time, do not introduce unnecessary complexity without justification.

Build the smallest architecture that can genuinely support the full requirements above.

When implementation decisions are ambiguous, choose the option that maximizes:

```textresearch reproducibility
visual realism
extensibility
maintainability
performance
```

The ultimate goal is to create a **general-purpose historical glyph simulation engine** capable of transforming SVG representations of writing systems into realistic synthetic manuscript/inscription imagery for computer-vision research.

The system should be useful not only for the current writing system, but for future historical scripts simply by adding their SVG glyph directories.

Treat this as a real software-engineering and computer-vision library intended for long-term research use, not as a temporary experiment.
