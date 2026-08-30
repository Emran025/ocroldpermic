import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_ar.dart';
import 'app_localizations_en.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
      : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations)!;
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
    delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
  ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('ar'),
    Locale('en')
  ];

  /// No description provided for @appName.
  ///
  /// In en, this message translates to:
  /// **'ARCHIVAL VISION LAB'**
  String get appName;

  /// No description provided for @appSubtitle.
  ///
  /// In en, this message translates to:
  /// **'OCR Runtime'**
  String get appSubtitle;

  /// No description provided for @toggleTheme.
  ///
  /// In en, this message translates to:
  /// **'Toggle color theme'**
  String get toggleTheme;

  /// No description provided for @introTitle.
  ///
  /// In en, this message translates to:
  /// **'Transcribe any supported writing system.'**
  String get introTitle;

  /// No description provided for @introBody.
  ///
  /// In en, this message translates to:
  /// **'Install a self-describing OCR package, select a manuscript image, and review a local, traceable transcription. The app is the runtime; the package supplies the model and alphabet.'**
  String get introBody;

  /// No description provided for @packageStep.
  ///
  /// In en, this message translates to:
  /// **'1. OCR package'**
  String get packageStep;

  /// No description provided for @packageDescription.
  ///
  /// In en, this message translates to:
  /// **'The package defines the script, alphabet, model, and preprocessing contract.'**
  String get packageDescription;

  /// No description provided for @inputStep.
  ///
  /// In en, this message translates to:
  /// **'2. Input image'**
  String get inputStep;

  /// No description provided for @inputDescription.
  ///
  /// In en, this message translates to:
  /// **'Use a photo, camera capture, or a validated remote image. Inference stays on-device.'**
  String get inputDescription;

  /// No description provided for @runStep.
  ///
  /// In en, this message translates to:
  /// **'3. Run & review'**
  String get runStep;

  /// No description provided for @runDescription.
  ///
  /// In en, this message translates to:
  /// **'Detection order is reconstructed into lines and every character remains inspectable.'**
  String get runDescription;

  /// No description provided for @reviewStep.
  ///
  /// In en, this message translates to:
  /// **'4. Inspect transcription'**
  String get reviewStep;

  /// No description provided for @noPackage.
  ///
  /// In en, this message translates to:
  /// **'No OCR package installed yet.'**
  String get noPackage;

  /// No description provided for @noImage.
  ///
  /// In en, this message translates to:
  /// **'No image selected'**
  String get noImage;

  /// No description provided for @noResult.
  ///
  /// In en, this message translates to:
  /// **'Your transcription, confidence data, and model traceability will appear here after OCR runs.'**
  String get noResult;

  /// No description provided for @manifestUrl.
  ///
  /// In en, this message translates to:
  /// **'Manifest URL'**
  String get manifestUrl;

  /// No description provided for @packageUrl.
  ///
  /// In en, this message translates to:
  /// **'Package URL'**
  String get packageUrl;

  /// No description provided for @importPackage.
  ///
  /// In en, this message translates to:
  /// **'Import package'**
  String get importPackage;

  /// No description provided for @checkUpdate.
  ///
  /// In en, this message translates to:
  /// **'Check update'**
  String get checkUpdate;

  /// No description provided for @remove.
  ///
  /// In en, this message translates to:
  /// **'Remove'**
  String get remove;

  /// No description provided for @gallery.
  ///
  /// In en, this message translates to:
  /// **'Gallery'**
  String get gallery;

  /// No description provided for @camera.
  ///
  /// In en, this message translates to:
  /// **'Camera'**
  String get camera;

  /// No description provided for @files.
  ///
  /// In en, this message translates to:
  /// **'Files'**
  String get files;

  /// No description provided for @imageUrl.
  ///
  /// In en, this message translates to:
  /// **'Image URL'**
  String get imageUrl;

  /// No description provided for @runOcr.
  ///
  /// In en, this message translates to:
  /// **'Run on-device OCR'**
  String get runOcr;

  /// No description provided for @runningOcr.
  ///
  /// In en, this message translates to:
  /// **'Running OCR…'**
  String get runningOcr;

  /// No description provided for @researchControls.
  ///
  /// In en, this message translates to:
  /// **'Research controls'**
  String get researchControls;

  /// No description provided for @researchDescription.
  ///
  /// In en, this message translates to:
  /// **'Confidence and suppression thresholds affect displayed detections, not model accuracy.'**
  String get researchDescription;

  /// No description provided for @confidenceThreshold.
  ///
  /// In en, this message translates to:
  /// **'Confidence threshold'**
  String get confidenceThreshold;

  /// No description provided for @iouThreshold.
  ///
  /// In en, this message translates to:
  /// **'IoU / NMS threshold'**
  String get iouThreshold;

  /// No description provided for @maximumDetections.
  ///
  /// In en, this message translates to:
  /// **'Maximum detections: {count}'**
  String maximumDetections(Object count);

  /// No description provided for @exportResult.
  ///
  /// In en, this message translates to:
  /// **'Export result'**
  String get exportResult;

  /// No description provided for @exportTxt.
  ///
  /// In en, this message translates to:
  /// **'Export TXT'**
  String get exportTxt;

  /// No description provided for @exportJson.
  ///
  /// In en, this message translates to:
  /// **'Export research JSON'**
  String get exportJson;

  /// No description provided for @exportCsv.
  ///
  /// In en, this message translates to:
  /// **'Export glyph CSV'**
  String get exportCsv;

  /// No description provided for @boxes.
  ///
  /// In en, this message translates to:
  /// **'Boxes'**
  String get boxes;

  /// No description provided for @labels.
  ///
  /// In en, this message translates to:
  /// **'Labels'**
  String get labels;

  /// No description provided for @confidence.
  ///
  /// In en, this message translates to:
  /// **'Confidence'**
  String get confidence;

  /// No description provided for @unicode.
  ///
  /// In en, this message translates to:
  /// **'Unicode'**
  String get unicode;

  /// No description provided for @editableTranscription.
  ///
  /// In en, this message translates to:
  /// **'Editable transcription'**
  String get editableTranscription;

  /// No description provided for @editedHelp.
  ///
  /// In en, this message translates to:
  /// **'Edited text is preserved separately from raw model output.'**
  String get editedHelp;

  /// No description provided for @rawHelp.
  ///
  /// In en, this message translates to:
  /// **'Raw model output; edits create a separate corrected transcription.'**
  String get rawHelp;

  /// No description provided for @selectGlyph.
  ///
  /// In en, this message translates to:
  /// **'Select a glyph in the image to inspect its class mapping and alternatives.'**
  String get selectGlyph;

  /// No description provided for @modelAlternatives.
  ///
  /// In en, this message translates to:
  /// **'Model alternatives'**
  String get modelAlternatives;

  /// No description provided for @packageLabel.
  ///
  /// In en, this message translates to:
  /// **'Package'**
  String get packageLabel;

  /// No description provided for @alphabetLabel.
  ///
  /// In en, this message translates to:
  /// **'Alphabet'**
  String get alphabetLabel;

  /// No description provided for @modelLabel.
  ///
  /// In en, this message translates to:
  /// **'Model'**
  String get modelLabel;

  /// No description provided for @runLabel.
  ///
  /// In en, this message translates to:
  /// **'Run'**
  String get runLabel;

  /// No description provided for @thresholdLabel.
  ///
  /// In en, this message translates to:
  /// **'Threshold'**
  String get thresholdLabel;

  /// No description provided for @cancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get cancel;

  /// No description provided for @verifyInstall.
  ///
  /// In en, this message translates to:
  /// **'Verify & install'**
  String get verifyInstall;

  /// No description provided for @downloadInstall.
  ///
  /// In en, this message translates to:
  /// **'Download & install'**
  String get downloadInstall;

  /// No description provided for @downloadImage.
  ///
  /// In en, this message translates to:
  /// **'Download image'**
  String get downloadImage;

  /// No description provided for @addOcrPackage.
  ///
  /// In en, this message translates to:
  /// **'Add OCR package'**
  String get addOcrPackage;

  /// No description provided for @installRemotePackage.
  ///
  /// In en, this message translates to:
  /// **'Install remote OCR package'**
  String get installRemotePackage;

  /// No description provided for @useRemoteImage.
  ///
  /// In en, this message translates to:
  /// **'Use remote image'**
  String get useRemoteImage;

  /// No description provided for @manifestHint.
  ///
  /// In en, this message translates to:
  /// **'https://example.org/manifest.json'**
  String get manifestHint;

  /// No description provided for @packageHint.
  ///
  /// In en, this message translates to:
  /// **'https://example.org/model.ocrpkg'**
  String get packageHint;

  /// No description provided for @imageHint.
  ///
  /// In en, this message translates to:
  /// **'https://example.org/manuscript.jpg'**
  String get imageHint;

  /// No description provided for @manifestLabel.
  ///
  /// In en, this message translates to:
  /// **'Package manifest URL'**
  String get manifestLabel;

  /// No description provided for @packageLabelInput.
  ///
  /// In en, this message translates to:
  /// **'OCR package URL'**
  String get packageLabelInput;

  /// No description provided for @imageLabel.
  ///
  /// In en, this message translates to:
  /// **'Image URL'**
  String get imageLabel;

  /// No description provided for @activePackage.
  ///
  /// In en, this message translates to:
  /// **'Active package'**
  String get activePackage;

  /// No description provided for @noModelGlyph.
  ///
  /// In en, this message translates to:
  /// **'Select a glyph in the image to inspect its class mapping and alternatives.'**
  String get noModelGlyph;

  /// No description provided for @shieldStatement.
  ///
  /// In en, this message translates to:
  /// **'Package checks, alphabet alignment, SHA-256 verification, and atomic activation protect the active model.'**
  String get shieldStatement;

  /// No description provided for @classesDetail.
  ///
  /// In en, this message translates to:
  /// **'{classes} classes · {format} · {width}×{height}'**
  String classesDetail(
      Object classes, Object format, Object height, Object width);

  /// No description provided for @alphabetDetail.
  ///
  /// In en, this message translates to:
  /// **'Alphabet v{version} · {direction}'**
  String alphabetDetail(Object direction, Object version);

  /// No description provided for @rtl.
  ///
  /// In en, this message translates to:
  /// **'RTL'**
  String get rtl;

  /// No description provided for @ltr.
  ///
  /// In en, this message translates to:
  /// **'LTR'**
  String get ltr;

  /// No description provided for @glyphSummary.
  ///
  /// In en, this message translates to:
  /// **'{count} glyphs · {confidence}% mean confidence · {milliseconds} ms'**
  String glyphSummary(Object confidence, Object count, Object milliseconds);

  /// No description provided for @classDetail.
  ///
  /// In en, this message translates to:
  /// **'{unicode} · class {id}\n{confidence}% confidence'**
  String classDetail(Object confidence, Object id, Object unicode);

  /// No description provided for @ocrPackageReady.
  ///
  /// In en, this message translates to:
  /// **'{name} is ready for offline OCR.'**
  String ocrPackageReady(Object name);

  /// No description provided for @noGlyphs.
  ///
  /// In en, this message translates to:
  /// **'No glyphs met the current confidence threshold.'**
  String get noGlyphs;

  /// No description provided for @exportCreated.
  ///
  /// In en, this message translates to:
  /// **'Export created: {path}'**
  String exportCreated(Object path);

  /// No description provided for @updateAvailable.
  ///
  /// In en, this message translates to:
  /// **'Update available: {version}. Open the package manager to install it.'**
  String updateAvailable(Object version);

  /// No description provided for @packageUpdated.
  ///
  /// In en, this message translates to:
  /// **'{name} updated successfully.'**
  String packageUpdated(Object name);

  /// No description provided for @installingUpdate.
  ///
  /// In en, this message translates to:
  /// **'Installing package update…'**
  String get installingUpdate;

  /// No description provided for @activeUpToDate.
  ///
  /// In en, this message translates to:
  /// **'The active OCR package is up to date.'**
  String get activeUpToDate;

  /// No description provided for @offline.
  ///
  /// In en, this message translates to:
  /// **'Offline. Installed OCR packages remain available.'**
  String get offline;

  /// No description provided for @noPackagesLoaded.
  ///
  /// In en, this message translates to:
  /// **'Installed OCR packages could not be loaded.'**
  String get noPackagesLoaded;

  /// No description provided for @invalidImageUrl.
  ///
  /// In en, this message translates to:
  /// **'Enter a valid image URL.'**
  String get invalidImageUrl;

  /// No description provided for @imageDownloadFailed.
  ///
  /// In en, this message translates to:
  /// **'The image URL could not be downloaded or decoded.'**
  String get imageDownloadFailed;

  /// No description provided for @invalidManifestUrl.
  ///
  /// In en, this message translates to:
  /// **'Enter a valid HTTP(S) package manifest URL.'**
  String get invalidManifestUrl;

  /// No description provided for @checkingPackage.
  ///
  /// In en, this message translates to:
  /// **'Checking OCR package…'**
  String get checkingPackage;

  /// No description provided for @downloadingPackage.
  ///
  /// In en, this message translates to:
  /// **'Downloading OCR package…'**
  String get downloadingPackage;

  /// No description provided for @downloadingImage.
  ///
  /// In en, this message translates to:
  /// **'Downloading image…'**
  String get downloadingImage;

  /// No description provided for @invalidRemotePackage.
  ///
  /// In en, this message translates to:
  /// **'The remote OCR package is invalid, unsafe, or could not be installed.'**
  String get invalidRemotePackage;

  /// No description provided for @missingPackage.
  ///
  /// In en, this message translates to:
  /// **'The selected OCR package is no longer available.'**
  String get missingPackage;

  /// No description provided for @validatingPackage.
  ///
  /// In en, this message translates to:
  /// **'Validating local OCR package…'**
  String get validatingPackage;

  /// No description provided for @invalidLocalPackage.
  ///
  /// In en, this message translates to:
  /// **'The local OCR package is invalid, unsafe, or incompatible.'**
  String get invalidLocalPackage;

  /// No description provided for @activatingPackage.
  ///
  /// In en, this message translates to:
  /// **'Activating {name}…'**
  String activatingPackage(Object name);

  /// No description provided for @activationFailed.
  ///
  /// In en, this message translates to:
  /// **'This OCR package could not be activated.'**
  String get activationFailed;

  /// No description provided for @removeActiveFailed.
  ///
  /// In en, this message translates to:
  /// **'The active OCR package cannot be removed. Activate a replacement first.'**
  String get removeActiveFailed;

  /// No description provided for @selectPackageFirst.
  ///
  /// In en, this message translates to:
  /// **'Install or select an OCR package before running OCR.'**
  String get selectPackageFirst;

  /// No description provided for @selectImageFirst.
  ///
  /// In en, this message translates to:
  /// **'Select, capture, or download an image before running OCR.'**
  String get selectImageFirst;

  /// No description provided for @ocrRunning.
  ///
  /// In en, this message translates to:
  /// **'Running on-device OCR…'**
  String get ocrRunning;

  /// No description provided for @ocrFailed.
  ///
  /// In en, this message translates to:
  /// **'OCR could not be completed. Check the image and selected model package.'**
  String get ocrFailed;

  /// No description provided for @exportFailed.
  ///
  /// In en, this message translates to:
  /// **'The OCR result could not be exported.'**
  String get exportFailed;

  /// No description provided for @checkingUpdates.
  ///
  /// In en, this message translates to:
  /// **'Checking for package updates…'**
  String get checkingUpdates;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['ar', 'en'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'ar':
      return AppLocalizationsAr();
    case 'en':
      return AppLocalizationsEn();
  }

  throw FlutterError(
      'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
      'an issue with the localizations generation tool. Please file an issue '
      'on GitHub with a reproducible sample app and the gen-l10n configuration '
      'that was used.');
}
