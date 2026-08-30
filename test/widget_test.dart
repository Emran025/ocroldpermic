import 'package:flutter_test/flutter_test.dart';
import 'package:old_permic_ocr_mobile/main.dart';

void main() {
  testWidgets('renders the generic OCR runtime workflow', (tester) async {
    await tester.pumpWidget(const OcrRuntimeApp(initialUpdateCheck: false));
    await tester.pump();

    expect(find.text('OCR Runtime'), findsOneWidget);
    expect(find.text('1. OCR package'), findsOneWidget);
    expect(find.text('Gallery'), findsOneWidget);
    expect(find.text('Camera'), findsOneWidget);
    expect(find.text('No OCR package installed yet.'), findsOneWidget);
  });
}
