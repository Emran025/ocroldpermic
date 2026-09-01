# Professional Specification Prompt — Generic Flutter OCR Runtime, Dynamic Model & Alphabet Delivery Platform

## Role

You are a senior Flutter architect, mobile machine-learning engineer, computer-vision engineer, MLOps engineer, API/data-contract designer, and Clean Architecture specialist.

You are working on an existing Flutter application that already follows a professional **Clean Architecture** structure.

Your task is to transform this application into a **generic, reusable OCR inference platform** capable of loading different OCR/detection models and historical writing systems without requiring the application itself to be rewritten.

The application must function as a reusable template.

It must not be hard-coded specifically for Old Permic.

The same application should theoretically support:

```text
Old Permic
Latin
Greek
Cyrillic
Arabic
historical scripts
other Unicode-based writing systems
```

provided that the appropriate model and alphabet/data package are supplied.

The application is the final consumer of the models produced by the previous training pipeline.

---

# 1. Core Concept

The application should operate around a dynamically supplied **OCR Model Package**.

Conceptually:

```text
                 OCR Application
                       │
              ┌────────┴────────┐
              │                 │
        Model Package       Test Image
              │                 │
              ▼                 ▼
        YOLO / OCR Engine → Detection
                              │
                              ▼
                         Recognition
                              │
                              ▼
                       Unicode Mapping
                              │
                              ▼
                         Text Output
```

The application itself should remain generic.

The model determines:

```text
classes
alphabet
Unicode mapping
model version
metadata
```

The application determines:

```text
inference
visualization
confidence
ordering
editing
export
model management
```

---

# 2. Existing Flutter Architecture

Do NOT rewrite the existing application unnecessarily.

First inspect the existing architecture.

Preserve:

```text
Clean Architecture
Domain
Data
Presentation
Dependency Injection
repositories
use cases
state management
existing UI conventions
```

Extend the existing architecture where appropriate.

Do not introduce a second competing architectural pattern.

---

# 3. Generic OCR Package

The central abstraction should be an OCR model package.

A package should contain sufficient information for the application to understand a model without hard-coded knowledge of the language.

Conceptually:

```text
ocr_package/
    manifest.json
    model/
        model.onnx / model.tflite / supported format
    alphabet/
        ...
    metadata/
        ...
```

The exact physical structure should be determined by implementation constraints.

The important requirement is that the package is **self-describing**.

---

# 4. Model Manifest

Every downloadable model must have a machine-readable manifest.

For example:

```json
{
  "package_id": "...",
  "language": "...",
  "script": "...",
  "version": "...",
  "model_version": "...",
  "model_format": "...",
  "classes": [],
  "alphabet_version": "...",
  "input_size": 640,
  "minimum_runtime_version": "...",
  "created_at": "...",
  "checksum": "...",
  "download_url": "..."
}
```

Do not assume this exact schema.

Design a robust versioned schema appropriate for the application.

---

# 5. Alphabet Definition

The alphabet must be delivered as data.

Do NOT hard-code the alphabet inside Dart source code.

For example:

```json
{
  "classes": [
    {
      "id": 0,
      "unicode": "U+10350",
      "character": "...",
      "name": "...",
      "display": "..."
    }
  ]
}
```

The actual schema may be improved.

The critical requirement is:

```text
model class ID
       ↓
alphabet mapping
       ↓
Unicode character
       ↓
rendered text
```

This allows the same application to work with completely different writing systems.

---

# 6. Model Selection

The user should be able to specify a model through a configurable source.

Support at least:

```text
local model
remote model URL
remote package URL
repository/release URL where appropriate
```

The application should not assume one permanent model URL.

For example:

```text
Model URL
    ↓
Download
    ↓
Verify
    ↓
Install
    ↓
Register
    ↓
Load
```

---

# 7. Remote Model Download

When a remote model is selected:

1. Retrieve the manifest.
2. Validate the manifest.
3. Determine package compatibility.
4. Download the required artifacts.
5. Verify integrity.
6. Extract/install them.
7. Register the model locally.
8. Make the model available to inference.

The download must be resumable where practical.

Do not leave partially downloaded models registered as valid models.

---

# 8. Model Updates

The application must support model updates naturally.

Conceptually:

```text
Installed Model v1
       ↓
Check for update
       ↓
Model v2 available
       ↓
Download
       ↓
Verify
       ↓
Install
       ↓
Switch active version
```

Do not destroy the currently working model before the new model has been successfully validated.

Use an atomic installation strategy:

```text
current/
candidate/
```

then:

```text
candidate validated
       ↓
activate candidate
```

This ensures that a failed update does not break the application.

---

# 9. Version Management

Support multiple installed model versions if practical.

Maintain:

```text
model ID
version
installation date
source
checksum
active/inactive state
```

The user should be able to identify which model produced a result.

---

# 10. Model Compatibility

Before loading a model, verify:

```text
model format
runtime compatibility
class count
alphabet compatibility
input dimensions
required preprocessing
minimum application version
```

If incompatible, produce a clear error.

Do not allow a corrupted or incompatible model to reach the inference engine.

---

# 11. Model Integrity

Model files and manifests must support integrity verification.

At minimum, support cryptographic checksums such as SHA-256.

Conceptually:

```text
download
   ↓
calculate hash
   ↓
compare expected hash
   ↓
valid?
   ├── YES → install
   └── NO  → reject
```

Never silently use a corrupted model.

---

# 12. Local Model Support

The application must also support local models.

Possible sources:

```text
application bundled model
device storage
imported model package
previously downloaded model
```

The exact UI should be determined by the existing application.

The inference layer should not care whether the model came from:

```text
URL
local storage
bundled assets
```

Use a common repository abstraction.

---

# 13. Model Repository Abstraction

Create a domain-level abstraction such as:

```text
ModelRepository
```

which handles:

```text
list models
get metadata
download model
install model
activate model
remove model
check update
```

The presentation layer must not directly manipulate files or URLs.

---

# 14. Image Input

The application must support three primary image sources:

```text
1. Remote image URL
2. Local/uploaded image
3. Camera capture
```

Conceptually:

```text
                Image Source
                     │
       ┌─────────────┼─────────────┐
       ▼             ▼             ▼
      URL          Gallery       Camera
       │             │             │
       └─────────────┼─────────────┘
                     ▼
              Image Preprocessor
                     ▼
                 Inference
```

---

# 15. Remote Image

The user should be able to provide an image URL.

The application should:

1. Validate the URL.
2. Download the image.
3. Validate the image.
4. Process it locally.
5. Never send the image to a remote inference server unless explicitly designed/configured to do so.

The default architecture should favor local inference when the model supports it.

---

# 16. Local Image

Support:

```text
gallery
file picker
application storage
```

The selected image should enter the same preprocessing pipeline as every other source.

Do not create separate inference implementations for each source.

---

# 17. Camera

Provide direct camera capture.

Conceptually:

```text
Camera
  ↓
Capture
  ↓
Preview
  ↓
Crop/adjust if needed
  ↓
Inference
```

The application should be able to process historical manuscript photographs directly.

Where appropriate, support:

```text
focus
exposure
image resolution
crop
rotation
```

without unnecessarily complicating the UI.

---

# 18. Image Preprocessing

Create a reusable preprocessing pipeline.

It may include:

```text
resize
orientation correction
crop
normalization
padding
format conversion
```

The preprocessing parameters should be driven by model metadata where necessary.

Do not assume that every model uses the same input dimensions or preprocessing.

---

# 19. Detection Pipeline

The primary model is a YOLO-based detector.

The application should:

```text
Image
 ↓
Preprocess
 ↓
YOLO inference
 ↓
Bounding boxes
 ↓
Class IDs
 ↓
Confidence
 ↓
Alphabet mapping
```

The inference implementation must be isolated behind an abstraction.

For example:

```text
InferenceEngine
```

so that another model runtime can be introduced later.

---

# 20. Detection Result Model

Represent every detected glyph using a structured domain object.

For example:

```text
GlyphDetection
    classId
    unicode
    character
    confidence
    boundingBox
    center
    order
```

Do not allow raw YOLO-specific structures to leak throughout the application.

---

# 21. Reading Order

Detection order must not simply follow YOLO output order.

The application must reconstruct logical reading order.

For a single line:

```text
left → right
```

For multi-line documents:

```text
top → bottom
+
left → right
```

The algorithm must be designed to tolerate:

```text
rotation
slanted lines
different spacing
irregular historical layouts
```

Do not assume that manuscript text is perfectly horizontal.

---

# 22. Multi-Line Recognition

The system must support:

```text
single glyph
single line
multiple lines
complete document
```

The same detection representation should support all cases.

Conceptually:

```text
Document
 ├── Line 1
 │    ├── Glyph
 │    ├── Glyph
 │    └── Glyph
 │
 ├── Line 2
 │    ├── Glyph
 │    └── Glyph
 │
 └── Line 3
      └── ...
```

---

# 23. Text Reconstruction

After sorting detections:

```text
Glyphs
 ↓
Lines
 ↓
Characters
 ↓
Unicode sequence
 ↓
Text
```

Produce reconstructed text.

For example:

```text
Detected:
A B C D

Output:
ABCD
```

The actual characters must come from the dynamically loaded alphabet.

---

# 24. Confidence Handling

Every character should retain its confidence.

Example:

```text
Character    Confidence
A            0.98
B            0.94
C            0.71
D            0.99
```

The application should expose confidence information without overwhelming normal users.

---

# 25. Confidence Visualization

Provide configurable visualization.

Possible modes:

```text
simple
detailed
debug
```

For example:

```text
simple:
show recognized text

detailed:
character + confidence

debug:
bounding box + class + Unicode + confidence
```

---

# 26. Alternative Predictions

Where the inference engine provides meaningful class probabilities or alternative candidates, expose them.

For example:

```text
Detected: U+1035X
Confidence: 0.72

Alternatives:
U+1035X — 0.72
U+1036X — 0.18
U+1034X — 0.07
```

Do not fabricate probabilities.

Only expose mathematically valid outputs from the model.

---

# 27. Low-Confidence Characters

Allow the user to identify uncertain characters.

For example:

```text
████ █?██ ████
```

or an equivalent UI.

The uncertain character should be selectable to show:

```text
cropped glyph
top predictions
confidence
Unicode
bounding box
```

This is particularly important for historical manuscripts.

---

# 28. Interactive Result Viewer

The application should provide a result view containing:

```text
original image
+
detected bounding boxes
+
recognized text
+
confidence
```

The user should be able to inspect detections visually.

Clicking a detected character should highlight the corresponding region.

---

# 29. Detection Overlay

Provide an overlay layer:

```text
Image
  +
Bounding boxes
  +
Character labels
  +
Confidence
```

The overlay should be independently toggleable.

Possible controls:

```text
Boxes ON/OFF
Labels ON/OFF
Confidence ON/OFF
Unicode ON/OFF
```

---

# 30. Text Editing

The generated text should be editable.

The application must distinguish:

```text
model output
```

from:

```text
user correction
```

Do not overwrite the raw inference result.

Maintain both:

```text
raw transcription
edited transcription
```

where appropriate.

---

# 31. Export

Support exporting recognized text.

Possible formats:

```text
TXT
JSON
CSV
```

depending on the application's requirements.

For research use, JSON should contain rich metadata.

For example:

```text
document
model version
timestamp
characters
Unicode
confidence
bounding boxes
```

---

# 32. Reproducibility

Every OCR result should be traceable to:

```text
model ID
model version
alphabet version
application version
timestamp
input image identifier/hash where appropriate
```

This is essential for research experiments.

---

# 33. Model Package and Alphabet Synchronization

A model and alphabet must not accidentally become mismatched.

For example:

```text
Model A
classes = 38
```

must not be paired with:

```text
Alphabet B
classes = 41
```

Validate:

```text
class count
class IDs
Unicode mapping
alphabet version
model manifest
```

before activation.

---

# 34. Generic Language Switching

The application should allow different OCR packages to coexist.

For example:

```text
Installed OCR Systems

Old Permic
Version 1.4

Historical Greek
Version 2.1

Historical Cyrillic
Version 1.0
```

Selecting one changes the active:

```text
model
alphabet
metadata
class mapping
```

without rebuilding the application.

---

# 35. Language-Agnostic UI

Do not write UI labels such as:

```text
Old Permic Character
```

into the application architecture.

Use dynamic metadata:

```text
language
script
alphabet
model name
```

The application should display the currently loaded OCR system.

---

# 36. Model Update Discovery

Support:

```text
Check for updates
```

against a configured remote manifest/index.

Conceptually:

```text
Installed version: 1.2
Remote version:    1.4

Update available
```

The update mechanism must not assume GitHub exclusively.

The source can be configurable.

---

# 37. GitHub Release Compatibility

The model-training pipeline may publish validated models through GitHub releases or another configured distribution mechanism.

The Flutter application should be able to consume a stable download URL or manifest.

Do not couple the Flutter domain layer directly to GitHub APIs.

Create a generic remote model provider.

A GitHub implementation can be one provider.

---

# 38. Offline-First Inference

Once a model is downloaded:

```text
Internet OFF
     ↓
Model remains available
     ↓
Image inference continues locally
```

The application should not require internet connectivity for ordinary inference.

Internet should primarily be required for:

```text
model download
model update
remote image retrieval
```

unless explicitly configured otherwise.

---

# 39. Storage Management

Manage downloaded model packages safely.

Provide information such as:

```text
model size
version
last used
active model
```

Support deleting inactive models.

Never delete the active model without an explicit safe replacement.

---

# 40. Security

Remote model and image sources are untrusted inputs.

Implement:

```text
HTTPS where available
checksum validation
safe archive extraction
path traversal protection
file type validation
size limits
```

Do not blindly extract arbitrary archives.

---

# 41. Performance

Inference must be optimized for mobile devices.

Consider:

```text
hardware acceleration where supported
model quantization
input resolution
memory reuse
isolate/background processing
image resizing
```

Do not optimize prematurely.

Measure actual performance.

---

# 42. Large Image Handling

Historical manuscript images may be very large.

Do not load unnecessarily huge images into memory.

Implement an image processing strategy that can handle:

```text
high-resolution scans
large photographs
multi-megapixel images
```

without causing memory crashes.

Where appropriate:

```text
decode at required resolution
tile
crop
resize
```

rather than loading the entire original image at maximum resolution.

---

# 43. Document Mode

The application should support a future/optional document mode.

Possible workflow:

```text
Large manuscript
      ↓
document segmentation
      ↓
regions/lines
      ↓
glyph detection
      ↓
text reconstruction
```

The architecture should not prevent this extension.

---

# 44. Debug / Research Mode

Provide a research/debug mode.

It should expose:

```text
model version
alphabet version
input dimensions
inference time
number of detections
confidence threshold
IoU threshold
class ID
Unicode
bounding boxes
```

This mode is particularly important during model development.

---

# 45. Adjustable Detection Threshold

Allow the user to adjust the confidence threshold.

For example:

```text
Confidence threshold
0.25 ─────────●──── 1.00
```

Changing it should affect displayed detections appropriately.

Do not confuse:

```text
model confidence
```

with:

```text
accuracy
```

The UI must label this correctly.

---

# 46. Adjustable IoU / NMS Configuration

If supported by the inference runtime, allow advanced users to configure:

```text
IoU threshold
NMS
maximum detections
```

These should preferably live in advanced/research settings.

Do not expose unnecessary technical controls to ordinary users by default.

---

# 47. Architecture

Use a structure similar to:

```text
lib/
    core/
    domain/
        entities/
        repositories/
        usecases/

    data/
        datasources/
        models/
        repositories/
        local/
        remote/

    inference/
        engine/
        preprocessing/
        postprocessing/
        reading_order/

    features/
        model_management/
        image_input/
        ocr/
        results/
        settings/
        export/

    presentation/
        pages/
        widgets/
        state/
```

Adapt this to the existing project rather than blindly replacing it.

---

# 48. Important Domain Use Cases

Create appropriate use cases such as:

```text
GetAvailableModels
DownloadModel
InstallModel
ValidateModel
ActivateModel
CheckModelUpdate
RemoveModel
ProcessImage
RunOCR
ReconstructText
GetDetectionDetails
ExportOCRResult
```

Names may be improved.

Keep business logic outside widgets.

---

# 49. State Management

Use the application's existing state-management solution if one exists.

Do not introduce a second state-management framework unnecessarily.

Model states should be explicit:

```text
idle
checking
downloading
validating
installing
ready
loading
running
completed
failed
```

---

# 50. Error Handling

Errors must be meaningful.

Examples:

```text
Model download failed
Invalid model package
Checksum mismatch
Unsupported model format
Alphabet mismatch
Insufficient storage
Image cannot be decoded
Camera unavailable
Inference failed
```

Do not expose raw stack traces to ordinary users.

Keep detailed diagnostics available in debug mode.

---

# 51. No Hard-Coded OCR Knowledge

This is one of the most important architectural requirements.

The application must NOT contain logic such as:

```dart
if (unicode == 'U+10350') ...
```

for individual characters.

Instead:

```text
Model Package
     ↓
Manifest
     ↓
Alphabet
     ↓
Runtime Mapping
```

The same application binary should be capable of working with a completely different alphabet.

---

# 52. Package Contract

Define a formal contract between:

```text
Training Pipeline
        ↓
Model Package
        ↓
Flutter Application
```

The training pipeline produces:

```text
model
alphabet
manifest
metadata
checksums
version
```

The Flutter application consumes that contract.

This contract must be versioned.

---

# 53. Training-to-App Compatibility

The application must be able to consume the models produced by the previous training pipeline without manual code changes.

The final training pipeline should therefore produce an application-compatible package.

The model release process should validate:

```text
model
+
manifest
+
alphabet
+
class mapping
+
runtime compatibility
```

before publishing.

---

# 54. Model Release Flow

The complete lifecycle should be:

```text
Synthetic Dataset
       ↓
Curriculum Training
       ↓
Adaptive Remediation
       ↓
Validation
       ↓
Release Model
       ↓
Package Model + Alphabet + Manifest
       ↓
Publish
       ↓
Flutter App
       ↓
Discover Update
       ↓
Download
       ↓
Validate
       ↓
Activate
```

---

# 55. Testing

Implement comprehensive tests.

At minimum:

```text
manifest parsing
alphabet parsing
Unicode mapping
class mapping
model compatibility
checksum verification
download interruption
resume download
invalid package
model installation
model activation
model update
rollback
image URL input
local image input
camera input
preprocessing
inference
reading order
multi-line reconstruction
confidence handling
export
```

Use mocked model engines where appropriate.

Do not require an actual GPU for unit tests.

---

# 56. Integration Tests

Create integration tests for the complete workflow:

```text
Model URL
 ↓
Download
 ↓
Verify
 ↓
Install
 ↓
Activate
 ↓
Image
 ↓
Inference
 ↓
Detection
 ↓
Unicode mapping
 ↓
Reading order
 ↓
Text
```

Also test:

```text
Update v1 → v2
```

and:

```text
failed v2 installation → continue using v1
```

---

# 57. UI Testing

Test at least:

```text
model selection
model download
download progress
update notification
image selection
camera capture
OCR execution
result display
confidence visualization
character inspection
text editing
export
error states
```

---

# 58. Research Reproducibility

The application should make it possible to answer:

```text
Which model produced this transcription?
Which alphabet mapping was used?
What version of the application was used?
What confidence threshold was active?
When was the inference performed?
```

This information should be included in research/debug metadata.

---

# 59. Final UX

The ordinary workflow should be extremely simple:

```text
1. Select OCR model
2. Select/capture image
3. Run OCR
4. Inspect detected text
5. Inspect uncertain characters if needed
6. Edit/correct text
7. Export
```

The complexity of the underlying ML system must not make the normal interface complicated.

---

# 60. Advanced Research Workflow

Researchers should additionally be able to:

```text
select model version
change confidence threshold
inspect bounding boxes
inspect Unicode
inspect alternative predictions
view inference time
compare model versions
export detailed JSON
```

---

# 61. Final Architectural Principle

The Flutter application is not the language.

The model package is the language.

The application is the runtime.

Therefore:

```text
APPLICATION
    =
generic OCR runtime

MODEL PACKAGE
    =
specific language/script knowledge
```

This separation is mandatory.

---

# 62. Final Deliverable

Produce a production-quality Flutter implementation that integrates with the existing Clean Architecture project.

Do not create a toy OCR demo.

The result must be:

```text
generic
modular
offline-capable
updateable
model-agnostic
language-agnostic
research-friendly
secure
testable
maintainable
```

The final application should allow a researcher to deploy the same Flutter application to entirely different historical writing systems simply by supplying a compatible model package.

The application should therefore behave as a **reusable OCR platform**, while the trained model and alphabet package provide the domain-specific intelligence.
