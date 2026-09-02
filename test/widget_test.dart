import 'package:flutter_test/flutter_test.dart';
import 'package:old_permic_ocr_mobile/main.dart';

void main() {
  testWidgets('renders the Old Permic OCR trial shell', (tester) async {
    await tester.pumpWidget(const OldPermicApp(initialUpdateCheck: false));
    await tester.pump();
    expect(find.text('مختبر البرمية القديمة'), findsOneWidget);
    expect(find.text('اختيار صورة'), findsOneWidget);
    expect(find.text('التقاط صورة'), findsOneWidget);
  });
}
