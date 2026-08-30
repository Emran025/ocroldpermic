// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appName => 'ARCHIVAL VISION LAB';

  @override
  String get appSubtitle => 'OCR Runtime';

  @override
  String get toggleTheme => 'Toggle color theme';

  @override
  String get introTitle => 'Transcribe any supported writing system.';

  @override
  String get introBody =>
      'Install a self-describing OCR package, select a manuscript image, and review a local, traceable transcription. The app is the runtime; the package supplies the model and alphabet.';

  @override
  String get packageStep => '1. OCR package';

  @override
  String get packageDescription =>
      'The package defines the script, alphabet, model, and preprocessing contract.';

  @override
  String get inputStep => '2. Input image';

  @override
  String get inputDescription =>
      'Use a photo, camera capture, or a validated remote image. Inference stays on-device.';

  @override
  String get runStep => '3. Run & review';

  @override
  String get runDescription =>
      'Detection order is reconstructed into lines and every character remains inspectable.';

  @override
  String get reviewStep => '4. Inspect transcription';

  @override
  String get noPackage => 'No OCR package installed yet.';

  @override
  String get noImage => 'No image selected';

  @override
  String get noResult =>
      'Your transcription, confidence data, and model traceability will appear here after OCR runs.';

  @override
  String get manifestUrl => 'Manifest URL';

  @override
  String get packageUrl => 'Package URL';

  @override
  String get importPackage => 'Import package';

  @override
  String get checkUpdate => 'Check update';

  @override
  String get remove => 'Remove';

  @override
  String get gallery => 'Gallery';

  @override
  String get camera => 'Camera';

  @override
  String get files => 'Files';

  @override
  String get imageUrl => 'Image URL';

  @override
  String get runOcr => 'Run on-device OCR';

  @override
  String get runningOcr => 'Running OCR…';

  @override
  String get researchControls => 'Research controls';

  @override
  String get researchDescription =>
      'Confidence and suppression thresholds affect displayed detections, not model accuracy.';

  @override
  String get confidenceThreshold => 'Confidence threshold';

  @override
  String get iouThreshold => 'IoU / NMS threshold';

  @override
  String maximumDetections(Object count) {
    return 'Maximum detections: $count';
  }

  @override
  String get exportResult => 'Export result';

  @override
  String get exportTxt => 'Export TXT';

  @override
  String get exportJson => 'Export research JSON';

  @override
  String get exportCsv => 'Export glyph CSV';

  @override
  String get boxes => 'Boxes';

  @override
  String get labels => 'Labels';

  @override
  String get confidence => 'Confidence';

  @override
  String get unicode => 'Unicode';

  @override
  String get editableTranscription => 'Editable transcription';

  @override
  String get editedHelp =>
      'Edited text is preserved separately from raw model output.';

  @override
  String get rawHelp =>
      'Raw model output; edits create a separate corrected transcription.';

  @override
  String get selectGlyph =>
      'Select a glyph in the image to inspect its class mapping and alternatives.';

  @override
  String get modelAlternatives => 'Model alternatives';

  @override
  String get packageLabel => 'Package';

  @override
  String get alphabetLabel => 'Alphabet';

  @override
  String get modelLabel => 'Model';

  @override
  String get runLabel => 'Run';

  @override
  String get thresholdLabel => 'Threshold';

  @override
  String get cancel => 'Cancel';

  @override
  String get verifyInstall => 'Verify & install';

  @override
  String get downloadInstall => 'Download & install';

  @override
  String get downloadImage => 'Download image';

  @override
  String get addOcrPackage => 'Add OCR package';

  @override
  String get installRemotePackage => 'Install remote OCR package';

  @override
  String get useRemoteImage => 'Use remote image';

  @override
  String get manifestHint => 'https://example.org/manifest.json';

  @override
  String get packageHint => 'https://example.org/model.ocrpkg';

  @override
  String get imageHint => 'https://example.org/manuscript.jpg';

  @override
  String get manifestLabel => 'Package manifest URL';

  @override
  String get packageLabelInput => 'OCR package URL';

  @override
  String get imageLabel => 'Image URL';

  @override
  String get activePackage => 'Active package';

  @override
  String get noModelGlyph =>
      'Select a glyph in the image to inspect its class mapping and alternatives.';

  @override
  String get shieldStatement =>
      'Package checks, alphabet alignment, SHA-256 verification, and atomic activation protect the active model.';

  @override
  String classesDetail(
      Object classes, Object format, Object height, Object width) {
    return '$classes classes · $format · $width×$height';
  }

  @override
  String alphabetDetail(Object direction, Object version) {
    return 'Alphabet v$version · $direction';
  }

  @override
  String get rtl => 'RTL';

  @override
  String get ltr => 'LTR';

  @override
  String glyphSummary(Object confidence, Object count, Object milliseconds) {
    return '$count glyphs · $confidence% mean confidence · $milliseconds ms';
  }

  @override
  String classDetail(Object confidence, Object id, Object unicode) {
    return '$unicode · class $id\n$confidence% confidence';
  }

  @override
  String ocrPackageReady(Object name) {
    return '$name is ready for offline OCR.';
  }

  @override
  String get noGlyphs => 'No glyphs met the current confidence threshold.';

  @override
  String exportCreated(Object path) {
    return 'Export created: $path';
  }

  @override
  String updateAvailable(Object version) {
    return 'Update available: $version. Open the package manager to install it.';
  }

  @override
  String packageUpdated(Object name) {
    return '$name updated successfully.';
  }

  @override
  String get installingUpdate => 'Installing package update…';

  @override
  String get activeUpToDate => 'The active OCR package is up to date.';

  @override
  String get offline => 'Offline. Installed OCR packages remain available.';

  @override
  String get noPackagesLoaded => 'Installed OCR packages could not be loaded.';

  @override
  String get invalidImageUrl => 'Enter a valid image URL.';

  @override
  String get imageDownloadFailed =>
      'The image URL could not be downloaded or decoded.';

  @override
  String get invalidManifestUrl =>
      'Enter a valid HTTP(S) package manifest URL.';

  @override
  String get checkingPackage => 'Checking OCR package…';

  @override
  String get downloadingPackage => 'Downloading OCR package…';

  @override
  String get downloadingImage => 'Downloading image…';

  @override
  String get invalidRemotePackage =>
      'The remote OCR package is invalid, unsafe, or could not be installed.';

  @override
  String get missingPackage =>
      'The selected OCR package is no longer available.';

  @override
  String get validatingPackage => 'Validating local OCR package…';

  @override
  String get invalidLocalPackage =>
      'The local OCR package is invalid, unsafe, or incompatible.';

  @override
  String activatingPackage(Object name) {
    return 'Activating $name…';
  }

  @override
  String get activationFailed => 'This OCR package could not be activated.';

  @override
  String get removeActiveFailed =>
      'The active OCR package cannot be removed. Activate a replacement first.';

  @override
  String get selectPackageFirst =>
      'Install or select an OCR package before running OCR.';

  @override
  String get selectImageFirst =>
      'Select, capture, or download an image before running OCR.';

  @override
  String get ocrRunning => 'Running on-device OCR…';

  @override
  String get ocrFailed =>
      'OCR could not be completed. Check the image and selected model package.';

  @override
  String get exportFailed => 'The OCR result could not be exported.';

  @override
  String get checkingUpdates => 'Checking for package updates…';
}
