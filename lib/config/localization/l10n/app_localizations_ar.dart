// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Arabic (`ar`).
class AppLocalizationsAr extends AppLocalizations {
  AppLocalizationsAr([String locale = 'ar']) : super(locale);

  @override
  String get appName => 'مختبر الرؤية الأرشيفية';

  @override
  String get appSubtitle => 'مشغّل OCR';

  @override
  String get toggleTheme => 'تبديل مظهر الألوان';

  @override
  String get introTitle => 'حوّل أي نظام كتابة مدعوم إلى نص.';

  @override
  String get introBody =>
      'ثبّت حزمة OCR ذاتية الوصف، واختر صورة مخطوطة، وراجع تفريغًا محليًا قابلًا للتتبع. التطبيق هو المشغّل، والحزمة توفر النموذج والأبجدية.';

  @override
  String get packageStep => '١. حزمة OCR';

  @override
  String get packageDescription =>
      'تحدد الحزمة الخط والأبجدية والنموذج وعقد المعالجة المسبقة.';

  @override
  String get inputStep => '٢. صورة الإدخال';

  @override
  String get inputDescription =>
      'استخدم صورة أو الكاميرا أو صورة بعيدة موثوقة. يبقى الاستدلال على الجهاز.';

  @override
  String get runStep => '٣. التشغيل والمراجعة';

  @override
  String get runDescription =>
      'يعاد ترتيب الكشفات إلى سطور وتبقى كل محرفة قابلة للفحص.';

  @override
  String get reviewStep => '٤. فحص التفريغ';

  @override
  String get noPackage => 'لا توجد حزمة OCR مثبتة بعد.';

  @override
  String get noImage => 'لم يتم اختيار صورة';

  @override
  String get noResult =>
      'سيظهر التفريغ وبيانات الثقة وقابلية تتبع النموذج بعد تشغيل OCR.';

  @override
  String get manifestUrl => 'رابط Manifest';

  @override
  String get packageUrl => 'رابط الحزمة';

  @override
  String get importPackage => 'استيراد حزمة';

  @override
  String get checkUpdate => 'فحص التحديث';

  @override
  String get remove => 'إزالة';

  @override
  String get gallery => 'المعرض';

  @override
  String get camera => 'الكاميرا';

  @override
  String get files => 'الملفات';

  @override
  String get imageUrl => 'رابط الصورة';

  @override
  String get runOcr => 'تشغيل OCR على الجهاز';

  @override
  String get runningOcr => 'جارٍ تشغيل OCR…';

  @override
  String get researchControls => 'أدوات البحث';

  @override
  String get researchDescription =>
      'تؤثر حدود الثقة والكبت في الكشفات المعروضة لا في دقة النموذج.';

  @override
  String get confidenceThreshold => 'حد الثقة';

  @override
  String get iouThreshold => 'حد IoU / NMS';

  @override
  String maximumDetections(Object count) {
    return 'الحد الأقصى للكشفات: $count';
  }

  @override
  String get exportResult => 'تصدير النتيجة';

  @override
  String get exportTxt => 'تصدير TXT';

  @override
  String get exportJson => 'تصدير JSON بحثي';

  @override
  String get exportCsv => 'تصدير CSV للمحارف';

  @override
  String get boxes => 'الصناديق';

  @override
  String get labels => 'التسميات';

  @override
  String get confidence => 'الثقة';

  @override
  String get unicode => 'Unicode';

  @override
  String get editableTranscription => 'تفريغ قابل للتحرير';

  @override
  String get editedHelp => 'يحفظ النص المعدل منفصلًا عن ناتج النموذج الخام.';

  @override
  String get rawHelp =>
      'ناتج النموذج الخام؛ تنشئ التعديلات تفريغًا مصححًا منفصلًا.';

  @override
  String get selectGlyph => 'اختر محرفة في الصورة لفحص ربط الفئة والبدائل.';

  @override
  String get modelAlternatives => 'بدائل النموذج';

  @override
  String get packageLabel => 'الحزمة';

  @override
  String get alphabetLabel => 'الأبجدية';

  @override
  String get modelLabel => 'النموذج';

  @override
  String get runLabel => 'التشغيل';

  @override
  String get thresholdLabel => 'الحد';

  @override
  String get cancel => 'إلغاء';

  @override
  String get verifyInstall => 'تحقق وثبّت';

  @override
  String get downloadInstall => 'نزّل وثبّت';

  @override
  String get downloadImage => 'تنزيل الصورة';

  @override
  String get addOcrPackage => 'إضافة حزمة OCR';

  @override
  String get installRemotePackage => 'تثبيت حزمة OCR بعيدة';

  @override
  String get useRemoteImage => 'استخدام صورة بعيدة';

  @override
  String get manifestHint => 'https://example.org/manifest.json';

  @override
  String get packageHint => 'https://example.org/model.ocrpkg';

  @override
  String get imageHint => 'https://example.org/manuscript.jpg';

  @override
  String get manifestLabel => 'رابط Manifest للحزمة';

  @override
  String get packageLabelInput => 'رابط حزمة OCR';

  @override
  String get imageLabel => 'رابط الصورة';

  @override
  String get activePackage => 'الحزمة النشطة';

  @override
  String get noModelGlyph => 'اختر محرفة في الصورة لفحص ربط الفئة والبدائل.';

  @override
  String get shieldStatement =>
      'تحمي فحوصات الحزمة ومحاذاة الأبجدية والتحقق من SHA-256 والتفعيل الذري النموذج النشط.';

  @override
  String classesDetail(
      Object classes, Object format, Object height, Object width) {
    return '$classes فئة · $format · $width×$height';
  }

  @override
  String alphabetDetail(Object direction, Object version) {
    return 'الأبجدية v$version · $direction';
  }

  @override
  String get rtl => 'من اليمين إلى اليسار';

  @override
  String get ltr => 'من اليسار إلى اليمين';

  @override
  String glyphSummary(Object confidence, Object count, Object milliseconds) {
    return '$count محرفة · متوسط الثقة $confidence% · $milliseconds مللي ثانية';
  }

  @override
  String classDetail(Object confidence, Object id, Object unicode) {
    return '$unicode · الفئة $id\nالثقة $confidence%';
  }

  @override
  String ocrPackageReady(Object name) {
    return '$name جاهزة للعمل دون اتصال.';
  }

  @override
  String get noGlyphs => 'لم تتجاوز أي محرفة حد الثقة الحالي.';

  @override
  String exportCreated(Object path) {
    return 'تم إنشاء التصدير: $path';
  }

  @override
  String updateAvailable(Object version) {
    return 'يتوفر تحديث: $version. افتح مدير الحزم لتثبيته.';
  }

  @override
  String packageUpdated(Object name) {
    return 'تم تحديث $name بنجاح.';
  }

  @override
  String get installingUpdate => 'جارٍ تثبيت تحديث الحزمة…';

  @override
  String get activeUpToDate => 'حزمة OCR النشطة محدثة.';

  @override
  String get offline => 'أنت غير متصل. تبقى حزم OCR المثبتة متاحة.';

  @override
  String get noPackagesLoaded => 'تعذر تحميل حزم OCR المثبتة.';

  @override
  String get invalidImageUrl => 'أدخل رابط صورة صحيحًا.';

  @override
  String get imageDownloadFailed => 'تعذر تنزيل الصورة البعيدة أو فكها.';

  @override
  String get invalidManifestUrl => 'أدخل رابط manifest صحيحًا عبر HTTP(S).';

  @override
  String get checkingPackage => 'جارٍ فحص حزمة OCR…';

  @override
  String get downloadingPackage => 'جارٍ تنزيل حزمة OCR…';

  @override
  String get downloadingImage => 'جارٍ تنزيل الصورة…';

  @override
  String get invalidRemotePackage =>
      'حزمة OCR البعيدة غير صالحة أو غير آمنة أو تعذر تثبيتها.';

  @override
  String get missingPackage => 'لم تعد حزمة OCR المحددة متاحة.';

  @override
  String get validatingPackage => 'جارٍ التحقق من حزمة OCR المحلية…';

  @override
  String get invalidLocalPackage =>
      'حزمة OCR المحلية غير صالحة أو غير آمنة أو غير متوافقة.';

  @override
  String activatingPackage(Object name) {
    return 'جارٍ تفعيل $name…';
  }

  @override
  String get activationFailed => 'تعذر تفعيل حزمة OCR هذه.';

  @override
  String get removeActiveFailed =>
      'لا يمكن إزالة حزمة OCR النشطة. فعّل بديلًا أولًا.';

  @override
  String get selectPackageFirst => 'ثبّت حزمة OCR أو اخترها قبل التشغيل.';

  @override
  String get selectImageFirst => 'اختر صورة أو التقطها أو نزّلها قبل التشغيل.';

  @override
  String get ocrRunning => 'جارٍ تشغيل OCR على الجهاز…';

  @override
  String get ocrFailed =>
      'تعذر إكمال OCR. تحقق من الصورة وحزمة النموذج المحددة.';

  @override
  String get exportFailed => 'تعذر تصدير نتيجة OCR.';

  @override
  String get checkingUpdates => 'جارٍ فحص تحديثات الحزمة…';
}
