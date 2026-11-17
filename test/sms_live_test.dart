import 'package:flutter_test/flutter_test.dart';

import 'package:finalcode/main.dart';

void main() {
  group('SmsLiveEvent', () {
    test('parses a received event', () {
      final event = SmsLiveEvent.fromMap({
        'type': 'received',
        'sender': 'Bank',
        'message': 'You paid 50 EGP',
        'date': 1735689600,
      });

      expect(event.type, 'received');
      expect(event.sender, 'Bank');
      expect(event.message, 'You paid 50 EGP');
      expect(event.date, 1735689600);
      expect(event.stored, 0);
      expect(event.pending, 0);
      expect(event.error, isNull);
    });

    test('parses a synced event', () {
      final event = SmsLiveEvent.fromMap({
        'type': 'synced',
        'stored': 2,
        'skipped': 1,
        'queued': 2,
        'pending': 0,
        'transactions_created': 1,
      });

      expect(event.type, 'synced');
      expect(event.stored, 2);
      expect(event.skipped, 1);
      expect(event.pending, 0);
      expect(event.transactionsCreated, 1);
    });

    test('defaults the transaction count to zero', () {
      final event = SmsLiveEvent.fromMap({
        'type': 'queue_flushed',
        'pending': 0,
      });

      expect(event.transactionsCreated, 0);
    });

    test('parses a failure event with an error message', () {
      final event = SmsLiveEvent.fromMap({
        'type': 'sync_failed',
        'pending': 3,
        'error': 'Connection refused',
      });

      expect(event.type, 'sync_failed');
      expect(event.pending, 3);
      expect(event.error, 'Connection refused');
    });

    test('tolerates missing fields', () {
      final event = SmsLiveEvent.fromMap({});

      expect(event.type, '');
      expect(event.sender, isNull);
      expect(event.date, isNull);
      expect(event.stored, 0);
    });
  });

  group('SmsFlushResult', () {
    test('reads the native flush payload', () {
      final result = SmsFlushResult.fromMap({
        'stored': 4,
        'skipped': 2,
        'failed': 0,
        'pending': 0,
        'transactions_created': 2,
      });

      expect(result.stored, 4);
      expect(result.skipped, 2);
      expect(result.failed, 0);
      expect(result.pending, 0);
      expect(result.transactionsCreated, 2);
      expect(result.error, isNull);
    });

    test('defaults to empty on a null payload', () {
      final result = SmsFlushResult.fromMap(null);

      expect(result.stored, 0);
      expect(result.pending, 0);
    });
  });

  group('DeviceSms', () {
    test('converts milliseconds to a DateTime', () {
      final sms = DeviceSms.fromMap({
        'id': 7,
        'sender': 'Bank',
        'message': 'Paid',
        'date': 1735689600000,
      });

      expect(sms.id, 7);
      expect(sms.sender, 'Bank');
      expect(
        sms.date.millisecondsSinceEpoch,
        1735689600000,
      );
    });
  });
}
