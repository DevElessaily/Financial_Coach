import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:finalcode/main.dart';

void main() {
  testWidgets('Add transaction form renders', (WidgetTester tester) async {
    tester.view.physicalSize = const Size(430, 932);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      const MaterialApp(home: AddTransactionPage()),
    );

    expect(find.text('New Transaction'), findsOneWidget);
    expect(find.text('Amount'), findsOneWidget);
    expect(find.text('Expense'), findsOneWidget);
    expect(find.text('Income'), findsOneWidget);
    expect(find.text('Transfer'), findsOneWidget);
  });
}
