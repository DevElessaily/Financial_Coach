import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'Services/VoiceRecorder/audio_utils.dart';
import 'Services/VoiceRecorder/models.dart';
import 'Services/VoiceRecorder/recorder.dart';

const _backendUrlPreference = 'backend_base_url';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final preferences = await SharedPreferences.getInstance();
  ApiConfig.baseUrl =
      preferences.getString(_backendUrlPreference) ?? ApiConfig.baseUrl;
  runApp(const FinanceApp());
}

// ---------------------------------------------------------------------------
// Theme tokens (sampled from the design)
// ---------------------------------------------------------------------------
class AppColors {
  static const bgTop = Color(0xFF0E3139);
  static const bgBottom = Color(0xFF041419);
  static const panel = Color(0x59000000); // black @ ~35%, sits on the gradient
  static const green = Color(0xFF2EF06F);
  static const chartGreen = Color(0xFF27D866);
  static const red = Color(0xFFFF4D4D);
  static const gold = Color(0xFFF5C518);
  static const muted = Color(0xFF9DB2B6);
  static const onGreen = Color(0xFF06262C);
  static const talabat = Color(0xFFFF5A00);
}

// ---------------------------------------------------------------------------
// Backend configuration + tiny API client
// ---------------------------------------------------------------------------
class ApiConfig {
  /// Android emulator -> 10.0.2.2 is the host machine.
  /// On a real phone, change this to your PC's LAN IP (e.g. 192.168.1.10).
  static String baseUrl = 'http://10.0.2.2:8000';

  static String get normalized {
    final raw = baseUrl.trim().replaceFirst(RegExp(r'/+$'), '');
    final uri = Uri.tryParse(raw);
    if (uri == null || uri.scheme != 'https' || !_isLocalHost(uri.host)) {
      return raw;
    }
    // The bundled FastAPI setup serves HTTP. Correct a common local setup
    // mistake while keeping HTTPS for public hosts.
    return uri
        .replace(scheme: 'http')
        .toString()
        .replaceFirst(RegExp(r'/+$'), '');
  }

  static bool _isLocalHost(String host) {
    final normalizedHost = host.toLowerCase();
    if (normalizedHost == 'localhost' ||
        normalizedHost == '10.0.2.2' ||
        normalizedHost == '::1' ||
        normalizedHost.endsWith('.local')) {
      return true;
    }

    final ipv4 = RegExp(
      r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$',
    ).firstMatch(normalizedHost);
    if (ipv4 == null) return false;
    final octets = [for (var i = 1; i <= 4; i++) int.parse(ipv4.group(i)!)];
    if (octets.any((octet) => octet > 255)) return false;
    return octets[0] == 10 ||
        octets[0] == 192 && octets[1] == 168 ||
        octets[0] == 172 && octets[1] >= 16 && octets[1] <= 31 ||
        octets[0] == 127;
  }
}

class ApiException implements Exception {
  ApiException(this.message);

  final String message;

  @override
  String toString() => message;
}

class Api {
  static const _timeout = Duration(seconds: 20);

  static Uri _uri(String path, [Map<String, String>? query]) {
    final uri = Uri.parse('${ApiConfig.normalized}$path');
    return query == null ? uri : uri.replace(queryParameters: query);
  }

  static String _detailText(dynamic detail) {
    if (detail is String) return detail;
    if (detail is List) {
      return detail
          .map((e) => e is Map ? (e['msg'] ?? e.toString()) : e.toString())
          .join('\n');
    }
    return detail.toString();
  }

  static dynamic _decode(http.Response response) {
    dynamic body;
    if (response.body.isNotEmpty) {
      try {
        body = jsonDecode(response.body);
      } catch (_) {
        body = response.body;
      }
    }

    if (response.statusCode < 200 || response.statusCode >= 300) {
      var message = 'HTTP ${response.statusCode}';
      if (body is Map && body['detail'] != null) {
        message = _detailText(body['detail']);
      }
      throw ApiException(message);
    }

    return body;
  }

  static Future<T> _guard<T>(Future<T> Function() call) async {
    try {
      return await call();
    } on ApiException {
      rethrow;
    } catch (error) {
      throw ApiException(
        'Could not reach ${ApiConfig.normalized}.\n'
        'Check that the backend is running and that the server URL in '
        'Settings points to your PC. Details: $error',
      );
    }
  }

  static Future<List<Map<String, dynamic>>> fetchTransactions({
    int limit = 20,
  }) {
    return _guard(() async {
      final response = await http
          .get(_uri('/api/transactions', {'limit': '$limit'}))
          .timeout(_timeout);
      final body = _decode(response);
      return (body as List)
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList();
    });
  }

  static Future<Map<String, dynamic>> createTransaction({
    required String amount,
    required String category,
    required String type,
    String? description,
    DateTime? date,
  }) {
    return _guard(() async {
      final response = await http
          .post(
            _uri('/api/transactions'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              'amount': amount,
              'category': category,
              'type': type,
              'description': description,
              'date': (date ?? DateTime.now()).toUtc().toIso8601String(),
            }),
          )
          .timeout(_timeout);
      return Map<String, dynamic>.from(_decode(response) as Map);
    });
  }

  static Future<List<Map<String, dynamic>>> fetchSmsHistory({int limit = 100}) {
    return _guard(() async {
      final response = await http
          .get(_uri('/api/sms/history', {'limit': '$limit'}))
          .timeout(_timeout);
      final body = _decode(response);
      return (body as List)
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList();
    });
  }

  static Future<Map<String, dynamic>> syncSms(
    List<Map<String, dynamic>> items,
  ) {
    return _guard(() async {
      final response = await http
          .post(
            _uri('/api/sms/bulk'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'items': items}),
          )
          .timeout(const Duration(seconds: 60));
      return Map<String, dynamic>.from(_decode(response) as Map);
    });
  }
}

// ---------------------------------------------------------------------------
// Device SMS inbox (Android method channel)
// ---------------------------------------------------------------------------
class DeviceSms {
  const DeviceSms({
    required this.id,
    required this.sender,
    required this.message,
    required this.date,
  });

  final int id;
  final String sender;
  final String message;
  final DateTime date;

  factory DeviceSms.fromMap(Map<dynamic, dynamic> map) {
    final millis = (map['date'] as num?)?.toInt() ?? 0;
    return DeviceSms(
      id: (map['id'] as num?)?.toInt() ?? 0,
      sender: '${map['sender'] ?? 'Unknown'}',
      message: '${map['message'] ?? ''}',
      date: DateTime.fromMillisecondsSinceEpoch(millis),
    );
  }
}

class SmsPermissionStatus {
  const SmsPermissionStatus({required this.canRead, required this.canReceive});

  final bool canRead;
  final bool canReceive;

  static const none = SmsPermissionStatus(canRead: false, canReceive: false);

  factory SmsPermissionStatus.fromMap(Map<dynamic, dynamic>? map) {
    if (map == null) return none;
    return SmsPermissionStatus(
      canRead: map['read'] == true,
      canReceive: map['receive'] == true,
    );
  }
}

class SmsFlushResult {
  const SmsFlushResult({
    this.stored = 0,
    this.skipped = 0,
    this.failed = 0,
    this.pending = 0,
    this.transactionsCreated = 0,
    this.error,
  });

  final int stored;
  final int skipped;
  final int failed;
  final int pending;
  final int transactionsCreated;
  final String? error;

  factory SmsFlushResult.fromMap(Map<dynamic, dynamic>? map) {
    if (map == null) return const SmsFlushResult();
    return SmsFlushResult(
      stored: (map['stored'] as num?)?.toInt() ?? 0,
      skipped: (map['skipped'] as num?)?.toInt() ?? 0,
      failed: (map['failed'] as num?)?.toInt() ?? 0,
      pending: (map['pending'] as num?)?.toInt() ?? 0,
      transactionsCreated: (map['transactions_created'] as num?)?.toInt() ?? 0,
      error: map['error'] as String?,
    );
  }
}

/// An event pushed from the native SMS receiver.
class SmsLiveEvent {
  const SmsLiveEvent({
    required this.type,
    this.sender,
    this.message,
    this.date,
    this.stored = 0,
    this.skipped = 0,
    this.pending = 0,
    this.transactionsCreated = 0,
    this.error,
  });

  /// `received`, `synced`, `sync_failed` or `queue_flushed`.
  final String type;
  final String? sender;
  final String? message;

  /// Epoch seconds, as sent by the native side.
  final int? date;

  final int stored;
  final int skipped;
  final int pending;

  /// How many transactions the backend detected in the uploaded SMS.
  final int transactionsCreated;

  final String? error;

  factory SmsLiveEvent.fromMap(Map<dynamic, dynamic> map) {
    return SmsLiveEvent(
      type: '${map['type'] ?? ''}',
      sender: map['sender'] as String?,
      message: map['message'] as String?,
      date: (map['date'] as num?)?.toInt(),
      stored: (map['stored'] as num?)?.toInt() ?? 0,
      skipped: (map['skipped'] as num?)?.toInt() ?? 0,
      pending: (map['pending'] as num?)?.toInt() ?? 0,
      transactionsCreated: (map['transactions_created'] as num?)?.toInt() ?? 0,
      error: map['error'] as String?,
    );
  }
}

class SmsReader {
  static const _channel = MethodChannel('com.example.finalcode/sms');

  static Future<bool> hasPermission() async {
    final granted = await _channel.invokeMethod<bool>('hasPermission');
    return granted ?? false;
  }

  static Future<SmsPermissionStatus> permissionStatus() async {
    final result = await _channel.invokeMethod<Map>('permissionStatus');
    return SmsPermissionStatus.fromMap(result);
  }

  static Future<bool> requestPermission() async {
    final granted = await _channel.invokeMethod<bool>('requestPermission');
    return granted ?? false;
  }

  static Future<void> openSettings() async {
    await _channel.invokeMethod<void>('openSettings');
  }

  static Future<List<DeviceSms>> readInbox({int limit = 200}) async {
    final result = await _channel.invokeMethod<List<dynamic>>('getInbox', {
      'limit': limit,
    });

    return (result ?? []).whereType<Map>().map(DeviceSms.fromMap).toList();
  }

  /// Sends SMS that were captured while the backend was unreachable.
  static Future<SmsFlushResult> flushPending() async {
    final result = await _channel.invokeMethod<Map>('flushPending');
    return SmsFlushResult.fromMap(result);
  }
}

/// Live stream of SMS captured by the native receiver.
class SmsLive {
  static const _channel = EventChannel('com.example.finalcode/sms_events');

  static Stream<SmsLiveEvent>? _stream;

  static Stream<SmsLiveEvent> get stream {
    return _stream ??= _channel
        .receiveBroadcastStream()
        .where((event) => event is Map)
        .map((event) => SmsLiveEvent.fromMap(event as Map));
  }
}

// ---------------------------------------------------------------------------
// Small shared helpers
// ---------------------------------------------------------------------------
String formatDate(DateTime? value) {
  if (value == null) return '';
  final local = value.toLocal();
  final now = DateTime.now();
  final sameDay =
      local.year == now.year &&
      local.month == now.month &&
      local.day == now.day;
  final hour = local.hour.toString().padLeft(2, '0');
  final minute = local.minute.toString().padLeft(2, '0');

  if (sameDay) return 'Today $hour:$minute';

  final day = local.day.toString().padLeft(2, '0');
  final month = local.month.toString().padLeft(2, '0');
  return '$day/$month/${local.year}  $hour:$minute';
}

DateTime? parseDate(dynamic value) {
  if (value is String) return DateTime.tryParse(value);
  return null;
}

Map<String, double> transactionTotalsByCurrency(
  List<Map<String, dynamic>> items,
  String type,
) {
  final totals = <String, double>{};
  for (final item in items.where((item) => item['type'] == type)) {
    final currency = '${item['currency'] ?? 'EGP'}'.toUpperCase();
    final amount = double.tryParse('${item['amount'] ?? 0}') ?? 0;
    totals[currency] = (totals[currency] ?? 0) + amount;
  }
  return totals;
}

String formatCurrencyTotals(Map<String, double> totals) {
  if (totals.isEmpty) return '0.00 EGP';
  final currencies = totals.keys.toList()..sort();
  return currencies
      .map((currency) => '${totals[currency]!.toStringAsFixed(2)} $currency')
      .join(' · ');
}

class FinanceApp extends StatelessWidget {
  const FinanceApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'Finance',
      theme: ThemeData(
        brightness: Brightness.dark,
        useMaterial3: true,
        scaffoldBackgroundColor: AppColors.bgBottom,
        colorScheme: ColorScheme.fromSeed(
          seedColor: AppColors.green,
          brightness: Brightness.dark,
        ),
        snackBarTheme: const SnackBarThemeData(
          behavior: SnackBarBehavior.floating,
        ),
      ),
      home: const HomeScreen(),
    );
  }
}

// ---------------------------------------------------------------------------
// Transaction insights and Wize spending helper
// ---------------------------------------------------------------------------
class InsightsPage extends StatefulWidget {
  const InsightsPage({super.key});

  @override
  State<InsightsPage> createState() => _InsightsPageState();
}

class _InsightsPageState extends State<InsightsPage> {
  List<Map<String, dynamic>> _items = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final items = await Api.fetchTransactions(limit: 200);
      if (!mounted) return;
      setState(() {
        _items = items;
        _loading = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = '$error';
        _loading = false;
      });
    }
  }

  double _value(Map<String, dynamic> item) =>
      double.tryParse('${item['amount'] ?? 0}') ?? 0;

  @override
  Widget build(BuildContext context) {
    final expenses = _items.where((item) => item['type'] == 'expense').toList();
    final incomeTotals = transactionTotalsByCurrency(_items, 'income');
    final expenseTotals = transactionTotalsByCurrency(_items, 'expense');
    final netTotals = <String, double>{};
    for (final currency in {...incomeTotals.keys, ...expenseTotals.keys}) {
      netTotals[currency] =
          (incomeTotals[currency] ?? 0) - (expenseTotals[currency] ?? 0);
    }
    final byCategory = <String, double>{};
    for (final item in expenses) {
      final category = '${item['category'] ?? 'Other'}';
      final currency = '${item['currency'] ?? 'EGP'}'.toUpperCase();
      final key = '$category · $currency';
      byCategory[key] = (byCategory[key] ?? 0) + _value(item);
    }
    final categories = byCategory.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));

    return Scaffold(
      backgroundColor: AppColors.bgBottom,
      appBar: AppBar(
        backgroundColor: AppColors.bgTop,
        title: const Text('Insights'),
      ),
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [AppColors.bgTop, AppColors.bgBottom],
          ),
        ),
        child: _loading
            ? const Center(
                child: CircularProgressIndicator(color: AppColors.green),
              )
            : _error != null
            ? Center(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: _PanelMessage(
                    text: _error!,
                    action: TextButton(
                      onPressed: _load,
                      child: const Text('Retry'),
                    ),
                  ),
                ),
              )
            : RefreshIndicator(
                onRefresh: _load,
                color: AppColors.green,
                child: ListView(
                  padding: const EdgeInsets.all(20),
                  children: [
                    const Text(
                      'Based on your latest 200 transactions',
                      style: TextStyle(color: AppColors.muted),
                    ),
                    const SizedBox(height: 14),
                    Row(
                      children: [
                        Expanded(
                          child: _InsightMetric(
                            label: 'Income',
                            amount: formatCurrencyTotals(incomeTotals),
                            color: AppColors.green,
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: _InsightMetric(
                            label: 'Spending',
                            amount: formatCurrencyTotals(expenseTotals),
                            color: AppColors.red,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    _InsightMetric(
                      label: 'Net cash flow',
                      amount: formatCurrencyTotals(netTotals),
                      color: netTotals.values.every((value) => value >= 0)
                          ? AppColors.green
                          : AppColors.red,
                    ),
                    const SizedBox(height: 24),
                    const Text(
                      'Spending by category',
                      style: TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 10),
                    if (categories.isEmpty)
                      const _PanelMessage(text: 'No expense transactions yet.')
                    else
                      for (final entry in categories)
                        Container(
                          margin: const EdgeInsets.only(bottom: 8),
                          padding: const EdgeInsets.all(14),
                          decoration: BoxDecoration(
                            color: AppColors.panel,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Row(
                            children: [
                              Expanded(
                                child: Text(
                                  entry.key,
                                  style: const TextStyle(
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                              ),
                              Text(
                                entry.value.toStringAsFixed(2),
                                style: const TextStyle(
                                  color: AppColors.red,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ],
                          ),
                        ),
                  ],
                ),
              ),
      ),
    );
  }
}

class _InsightMetric extends StatelessWidget {
  const _InsightMetric({
    required this.label,
    required this.amount,
    required this.color,
  });
  final String label;
  final String amount;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(
      color: AppColors.panel,
      borderRadius: BorderRadius.circular(12),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(fontSize: 12, color: AppColors.muted),
        ),
        const SizedBox(height: 6),
        Text(
          amount,
          style: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.w800,
            color: color,
          ),
        ),
      ],
    ),
  );
}

class WizePage extends StatefulWidget {
  const WizePage({super.key});

  @override
  State<WizePage> createState() => _WizePageState();
}

class _WizePageState extends State<WizePage> {
  final _question = TextEditingController();
  final List<Map<String, String>> _messages = [
    {
      'role': 'assistant',
      'text':
          'I can summarize your recorded income and spending. Try “How much did I spend?” or “What is my biggest expense?”',
    },
  ];
  List<Map<String, dynamic>> _items = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _question.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final items = await Api.fetchTransactions(limit: 200);
      if (mounted) {
        setState(() {
          _items = items;
          _loading = false;
        });
      }
    } catch (error) {
      if (mounted) {
        setState(() {
          _loading = false;
          _messages.add({
            'role': 'assistant',
            'text': 'I could not load transactions: $error',
          });
        });
      }
    }
  }

  double _value(Map<String, dynamic> item) =>
      double.tryParse('${item['amount'] ?? 0}') ?? 0;

  void _ask() {
    final question = _question.text.trim();
    if (question.isEmpty || _loading) return;
    final lower = question.toLowerCase();
    final expenses = _items.where((item) => item['type'] == 'expense').toList();
    final incomeTotals = transactionTotalsByCurrency(_items, 'income');
    final expenseTotals = transactionTotalsByCurrency(_items, 'expense');
    String answer;
    if (lower.contains('biggest') || lower.contains('largest')) {
      final biggest = expenses.isEmpty
          ? null
          : expenses.reduce((a, b) => _value(a) >= _value(b) ? a : b);
      answer = biggest == null
          ? 'There are no expense transactions recorded yet.'
          : 'Your largest recorded expense is ${_value(biggest).toStringAsFixed(2)} ${biggest['currency'] ?? 'EGP'} for ${biggest['description'] ?? biggest['category'] ?? 'Other'}.';
    } else if (lower.contains('categor')) {
      final categories = <String, double>{};
      for (final item in expenses) {
        final category = '${item['category'] ?? 'Other'}';
        final currency = '${item['currency'] ?? 'EGP'}'.toUpperCase();
        final key = '$category ($currency)';
        categories[key] = (categories[key] ?? 0) + _value(item);
      }
      final top = categories.entries.toList()
        ..sort((a, b) => b.value.compareTo(a.value));
      answer = top.isEmpty
          ? 'There are no expense transactions recorded yet.'
          : 'Your highest spending category is ${top.first.key}: ${top.first.value.toStringAsFixed(2)}.';
    } else if (lower.contains('income') || lower.contains('earn')) {
      answer =
          'Your recorded income totals ${formatCurrencyTotals(incomeTotals)} across the latest ${_items.length} transactions.';
    } else if (lower.contains('spend') ||
        lower.contains('expense') ||
        lower.contains('cash flow')) {
      final net = <String, double>{};
      for (final currency in {...incomeTotals.keys, ...expenseTotals.keys}) {
        net[currency] =
            (incomeTotals[currency] ?? 0) - (expenseTotals[currency] ?? 0);
      }
      answer =
          'Recorded expenses: ${formatCurrencyTotals(expenseTotals)}. Income: ${formatCurrencyTotals(incomeTotals)}. Net by currency: ${formatCurrencyTotals(net)}.';
    } else {
      answer =
          'You have ${_items.length} transactions loaded: ${formatCurrencyTotals(incomeTotals)} income and ${formatCurrencyTotals(expenseTotals)} expenses. Ask about spending, income, categories, or your biggest expense.';
    }
    setState(() {
      _messages.add({'role': 'user', 'text': question});
      _messages.add({'role': 'assistant', 'text': answer});
      _question.clear();
    });
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: AppColors.bgBottom,
    appBar: AppBar(backgroundColor: AppColors.bgTop, title: const Text('Wize')),
    body: Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [AppColors.bgTop, AppColors.bgBottom],
        ),
      ),
      child: Column(
        children: [
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: _messages.length,
              itemBuilder: (context, index) {
                final message = _messages[index];
                final isUser = message['role'] == 'user';
                return Align(
                  alignment: isUser
                      ? Alignment.centerRight
                      : Alignment.centerLeft,
                  child: Container(
                    constraints: const BoxConstraints(maxWidth: 320),
                    margin: const EdgeInsets.only(bottom: 10),
                    padding: const EdgeInsets.all(13),
                    decoration: BoxDecoration(
                      color: isUser
                          ? AppColors.green.withAlpha(45)
                          : AppColors.panel,
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Text(message['text'] ?? ''),
                  ),
                );
              },
            ),
          ),
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(14, 8, 14, 14),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _question,
                      enabled: !_loading,
                      onSubmitted: (_) => _ask(),
                      decoration: const InputDecoration(
                        hintText: 'Ask about your transactions',
                        filled: true,
                        border: OutlineInputBorder(),
                      ),
                    ),
                  ),
                  IconButton(
                    onPressed: _ask,
                    icon: const Icon(
                      Icons.send_rounded,
                      color: AppColors.green,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    ),
  );
}

// ---------------------------------------------------------------------------
// Home screen
// ---------------------------------------------------------------------------
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _tab = 0;

  List<Map<String, dynamic>> _allTransactions = [];
  List<Map<String, dynamic>> _recent = [];
  bool _loadingRecent = true;
  String? _recentError;

  @override
  void initState() {
    super.initState();
    _loadRecent();
  }

  Future<void> _loadRecent() async {
    setState(() {
      _loadingRecent = true;
      _recentError = null;
    });

    try {
      final items = await Api.fetchTransactions(limit: 200);
      if (!mounted) return;
      setState(() {
        _allTransactions = items;
        _recent = items.take(4).toList();
        _loadingRecent = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _recentError = '$error';
        _loadingRecent = false;
      });
    }
  }

  Future<void> _openAddTransaction({String? initialText}) async {
    final saved = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => AddTransactionPage(initialText: initialText),
      ),
    );

    if (saved == true && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Transaction saved'),
          backgroundColor: AppColors.chartGreen,
        ),
      );
      _loadRecent();
    }
  }

  void _openSmsHistory() {
    Navigator.of(
      context,
    ).push(MaterialPageRoute(builder: (_) => const SmsHistoryPage()));
  }

  void _openSettings() {
    Navigator.of(
      context,
    ).push(MaterialPageRoute(builder: (_) => const SettingsPage()));
  }

  void _openInsights() {
    Navigator.of(
      context,
    ).push(MaterialPageRoute(builder: (_) => const InsightsPage()));
  }

  void _openWize() {
    Navigator.of(
      context,
    ).push(MaterialPageRoute(builder: (_) => const WizePage()));
  }

  Future<void> _startVoiceEntry() async {
    final transcript = await showDialog<String>(
      context: context,
      barrierDismissible: false,
      builder: (_) => _VoiceRecordingDialog(recorder: VoiceRecorder()),
    );
    if (!mounted || transcript == null || transcript.trim().isEmpty) return;
    await _openAddTransaction(
      initialText: normalizeVoiceTranscript(transcript),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 430),
          child: DecoratedBox(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [AppColors.bgTop, AppColors.bgBottom],
              ),
            ),
            child: Stack(
              children: [
                SafeArea(
                  bottom: false,
                  child: RefreshIndicator(
                    color: AppColors.green,
                    backgroundColor: AppColors.bgTop,
                    onRefresh: _loadRecent,
                    child: SingleChildScrollView(
                      physics: const AlwaysScrollableScrollPhysics(),
                      padding: const EdgeInsets.fromLTRB(20, 24, 20, 130),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Good Morning',
                            style: TextStyle(
                              fontSize: 18,
                              color: Colors.white70,
                              fontWeight: FontWeight.w400,
                            ),
                          ),
                          const Text(
                            'Your account',
                            style: TextStyle(
                              fontSize: 36,
                              fontWeight: FontWeight.w800,
                              height: 1.15,
                            ),
                          ),
                          const SizedBox(height: 14),
                          _BankCard(
                            name: 'Tracked transactions',
                            balance: '${_allTransactions.length} records',
                          ),
                          const SizedBox(height: 12),
                          Row(
                            children: [
                              Expanded(
                                child: _ActionButton(
                                  label: 'Add Transaction',
                                  icon: Icons.add,
                                  filled: true,
                                  onTap: _openAddTransaction,
                                ),
                              ),
                              const SizedBox(width: 10),
                              Expanded(
                                child: _ActionButton(
                                  label: 'SMS History',
                                  icon: Icons.sms_outlined,
                                  filled: false,
                                  onTap: _openSmsHistory,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 18),
                          _SectionHeader(
                            title: 'Insights',
                            onViewAll: _openInsights,
                          ),
                          const SizedBox(height: 8),
                          Container(
                            width: double.infinity,
                            padding: const EdgeInsets.all(16),
                            decoration: BoxDecoration(
                              color: AppColors.panel,
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: Text(
                              _loadingRecent
                                  ? 'Loading your transaction summary…'
                                  : '${_allTransactions.length} transactions loaded. View Insights for totals by currency and spending category.',
                              style: const TextStyle(
                                color: AppColors.muted,
                                height: 1.4,
                              ),
                            ),
                          ),
                          const SizedBox(height: 16),
                          _SectionHeader(
                            title: 'Recent Activity',
                            actionLabel: 'Refresh',
                            onViewAll: _loadRecent,
                          ),
                          const SizedBox(height: 8),
                          ..._buildRecentActivity(),
                        ],
                      ),
                    ),
                  ),
                ),
                Positioned(
                  left: 0,
                  right: 0,
                  bottom: 0,
                  child: _BottomNav(
                    index: _tab,
                    onTab: (i) {
                      if (i == 3) {
                        _openSettings();
                      } else if (i == 1) {
                        _openInsights();
                      } else if (i == 2) {
                        _openWize();
                      } else {
                        setState(() => _tab = 0);
                      }
                    },
                    onVoice: _startVoiceEntry,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  List<Widget> _buildRecentActivity() {
    if (_loadingRecent) {
      return const [
        _PanelMessage(text: 'Loading transactions…', showSpinner: true),
      ];
    }

    if (_recentError != null) {
      return [
        _PanelMessage(
          text: _recentError!,
          action: TextButton(
            onPressed: _loadRecent,
            child: const Text('Retry'),
          ),
        ),
      ];
    }

    if (_recent.isEmpty) {
      return const [
        _PanelMessage(
          text: 'No transactions yet. Tap "Add Transaction" to create one.',
        ),
      ];
    }

    return [
      for (final transaction in _recent)
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: _TransactionTile(
            category: '${transaction['category'] ?? 'Other'}',
            description: '${transaction['description'] ?? ''}',
            amount: '${transaction['amount'] ?? '0'}',
            currency: '${transaction['currency'] ?? 'EGP'}',
            type: '${transaction['type'] ?? 'expense'}',
            date: parseDate(transaction['date']),
          ),
        ),
    ];
  }
}

class _VoiceRecordingDialog extends StatefulWidget {
  const _VoiceRecordingDialog({required this.recorder});

  final VoiceRecorder recorder;

  @override
  State<_VoiceRecordingDialog> createState() => _VoiceRecordingDialogState();
}

class _VoiceRecordingDialogState extends State<_VoiceRecordingDialog> {
  StreamSubscription<VoiceRecorderEvent>? _events;
  String _partial = '';
  String _status = 'Requesting microphone access…';
  bool _listening = false;
  bool _processing = false;
  bool _starting = false;

  @override
  void initState() {
    super.initState();
    _events = widget.recorder.events.listen(_onEvent);
    WidgetsBinding.instance.addPostFrameCallback((_) => _begin());
  }

  void _onEvent(VoiceRecorderEvent event) {
    if (!mounted) return;
    setState(() {
      switch (event.type) {
        case VoiceRecorderEventType.ready:
          _status = 'Listening… Speak clearly, then tap Stop.';
          _listening = true;
          _processing = false;
          break;
        case VoiceRecorderEventType.listening:
          _status = 'Listening… Speak clearly, then tap Stop.';
          _listening = true;
          _processing = false;
          break;
        case VoiceRecorderEventType.partial:
          _partial = event.transcript ?? _partial;
          _status = 'Listening…';
          _listening = true;
          break;
        case VoiceRecorderEventType.processing:
          _status = 'Processing your speech…';
          _listening = false;
          _processing = true;
          break;
        case VoiceRecorderEventType.cancelled:
          _status = 'Recording cancelled.';
          _listening = false;
          _processing = false;
          break;
        case VoiceRecorderEventType.completed:
          _partial = event.transcript ?? _partial;
          break;
        case VoiceRecorderEventType.error:
          _status = event.message ?? 'Voice recognition failed. Try again.';
          _listening = false;
          _processing = false;
          break;
        case VoiceRecorderEventType.unknown:
          if (event.message != null) _status = event.message!;
          break;
      }
    });
  }

  Future<void> _begin() async {
    if (_starting) return;
    setState(() {
      _starting = true;
      _partial = '';
      _status = 'Requesting microphone access…';
    });
    try {
      final text = await widget.recorder.start();
      if (!mounted) return;
      if (text != null && text.trim().isNotEmpty) {
        Navigator.of(context).pop(text.trim());
      } else {
        setState(() {
          _starting = false;
          _listening = false;
          _processing = false;
          _status = 'No speech was recognized. Try again.';
        });
      }
    } on PlatformException catch (error) {
      if (!mounted) return;
      setState(() {
        _starting = false;
        _listening = false;
        _processing = false;
        _status = error.message ?? 'Voice recognition could not start.';
      });
    } on MissingPluginException {
      if (!mounted) return;
      setState(() {
        _starting = false;
        _status = 'Voice recording is available in the Android app.';
      });
    }
  }

  Future<void> _stop() async {
    if (!_listening) return;
    setState(() {
      _listening = false;
      _processing = true;
      _status = 'Processing your speech…';
    });
    try {
      await widget.recorder.stop();
    } on PlatformException catch (error) {
      if (!mounted) return;
      setState(() {
        _processing = false;
        _status = error.message ?? 'Could not stop the recording.';
      });
    }
  }

  Future<void> _cancel() async {
    try {
      await widget.recorder.cancel();
    } on PlatformException {
      // The dialog can still close if the platform already ended recognition.
    }
    if (mounted) Navigator.of(context).pop();
  }

  @override
  void dispose() {
    _events?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      child: AlertDialog(
        backgroundColor: AppColors.bgTop,
        title: const Text('Voice transaction'),
        content: SizedBox(
          width: 360,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                width: 88,
                height: 88,
                decoration: BoxDecoration(
                  color: _listening
                      ? AppColors.red.withAlpha(35)
                      : AppColors.green.withAlpha(25),
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  _listening ? Icons.mic_rounded : Icons.graphic_eq_rounded,
                  size: 42,
                  color: _listening ? AppColors.red : AppColors.green,
                ),
              ),
              const SizedBox(height: 16),
              Text(_status, textAlign: TextAlign.center),
              const SizedBox(height: 12),
              Container(
                width: double.infinity,
                constraints: const BoxConstraints(minHeight: 64),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppColors.panel,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  _partial.isEmpty ? 'Your words will appear here' : _partial,
                  style: TextStyle(
                    color: _partial.isEmpty ? AppColors.muted : Colors.white,
                  ),
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: _cancel, child: const Text('Cancel')),
          if (_listening)
            FilledButton.icon(
              onPressed: _stop,
              icon: const Icon(Icons.stop_rounded),
              label: const Text('Stop'),
            )
          else if (!_processing)
            FilledButton.icon(
              onPressed: _begin,
              icon: const Icon(Icons.mic_rounded),
              label: Text(_starting ? 'Start again' : 'Try again'),
            )
          else
            const Padding(
              padding: EdgeInsets.all(12),
              child: SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
            ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Bank card
// ---------------------------------------------------------------------------
class _BankCard extends StatelessWidget {
  const _BankCard({required this.name, required this.balance});
  final String name;
  final String balance;

  @override
  Widget build(BuildContext context) {
    return AspectRatio(
      aspectRatio: 2.05,
      child: Container(
        padding: const EdgeInsets.fromLTRB(14, 0, 14, 10),
        decoration: BoxDecoration(
          color: Colors.black,
          borderRadius: BorderRadius.circular(14),
        ),
        child: Stack(
          children: [
            const Center(
              child: SizedBox(
                width: 78,
                height: 50,
                child: CustomPaint(painter: _TildePainter()),
              ),
            ),
            Align(
              alignment: Alignment.bottomCenter,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    name,
                    style: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  Text(
                    balance,
                    style: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// The white "~" brand mark on the card.
class _TildePainter extends CustomPainter {
  const _TildePainter();

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width, h = size.height;
    final path = Path()
      ..moveTo(0.06 * w, 0.66 * h)
      ..cubicTo(0.16 * w, 0.02 * h, 0.42 * w, 0.02 * h, 0.5 * w, 0.5 * h)
      ..cubicTo(0.58 * w, 0.98 * h, 0.84 * w, 0.98 * h, 0.94 * w, 0.34 * h);
    canvas.drawPath(
      path,
      Paint()
        ..color = Colors.white
        ..style = PaintingStyle.stroke
        ..strokeWidth = h * 0.26
        ..strokeCap = StrokeCap.round,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

// ---------------------------------------------------------------------------
// Buttons & headers
// ---------------------------------------------------------------------------
class _ActionButton extends StatelessWidget {
  const _ActionButton({
    required this.label,
    required this.icon,
    required this.filled,
    required this.onTap,
  });

  final String label;
  final IconData icon;
  final bool filled;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final fg = filled ? AppColors.onGreen : Colors.white;
    return Material(
      color: filled ? AppColors.green : const Color(0x33000000),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
        side: filled
            ? BorderSide.none
            : const BorderSide(color: Colors.white70, width: 1),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: onTap,
        child: SizedBox(
          height: 38,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: 18, color: fg),
              const SizedBox(width: 6),
              Flexible(
                child: Text(
                  label,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: fg,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({
    required this.title,
    required this.onViewAll,
    this.actionLabel = 'View all',
  });

  final String title;
  final VoidCallback onViewAll;
  final String actionLabel;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        Text(
          title,
          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w500),
        ),
        GestureDetector(
          onTap: onViewAll,
          child: Text(
            actionLabel,
            style: const TextStyle(
              fontSize: 12,
              decoration: TextDecoration.underline,
              decorationColor: Colors.white,
            ),
          ),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Stocks & activity
// ---------------------------------------------------------------------------
class _StockTile extends StatelessWidget {
  const _StockTile({
    required this.symbol,
    required this.price,
    required this.dot,
    required this.up,
  });

  final String symbol;
  final String price;
  final Color dot;
  final bool up;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(10, 10, 10, 10),
      decoration: BoxDecoration(
        color: AppColors.panel,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 5,
                height: 5,
                decoration: BoxDecoration(color: dot, shape: BoxShape.circle),
              ),
              const SizedBox(width: 5),
              Text(
                symbol,
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w800,
                  color: dot == Colors.white ? Colors.white : dot,
                ),
              ),
              const Spacer(),
              Icon(
                up ? Icons.trending_up : Icons.trending_down,
                size: 14,
                color: up ? AppColors.green : AppColors.red,
              ),
            ],
          ),
          const SizedBox(height: 8),
          FittedBox(
            fit: BoxFit.scaleDown,
            child: Text(
              price,
              style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w400),
            ),
          ),
        ],
      ),
    );
  }
}

class _TransactionTile extends StatelessWidget {
  const _TransactionTile({
    required this.category,
    required this.description,
    required this.amount,
    required this.currency,
    required this.type,
    required this.date,
  });

  final String category;
  final String description;
  final String amount;
  final String currency;
  final String type;
  final DateTime? date;

  @override
  Widget build(BuildContext context) {
    final isIncome = type == 'income';
    final isTransfer = type == 'transfer';
    final color = isIncome
        ? AppColors.chartGreen
        : isTransfer
        ? AppColors.gold
        : AppColors.red;
    final icon = isIncome
        ? Icons.south_west_rounded
        : isTransfer
        ? Icons.swap_horiz_rounded
        : Icons.north_east_rounded;

    final sign = isIncome
        ? '+'
        : isTransfer
        ? ''
        : '-';

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.panel,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Container(
            width: 38,
            height: 38,
            decoration: BoxDecoration(
              color: color.withAlpha(38),
              borderRadius: BorderRadius.circular(9),
            ),
            child: Icon(icon, color: color, size: 22),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  category,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                if (description.isNotEmpty)
                  Text(
                    description,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 11, color: Colors.white54),
                  ),
                if (date != null)
                  Text(
                    formatDate(date),
                    style: const TextStyle(
                      fontSize: 10,
                      color: AppColors.muted,
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Text(
            '$sign$amount $currency',
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w700,
              color: color,
            ),
          ),
        ],
      ),
    );
  }
}

class _PanelMessage extends StatelessWidget {
  const _PanelMessage({
    required this.text,
    this.showSpinner = false,
    this.action,
  });

  final String text;
  final bool showSpinner;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.panel,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (showSpinner) ...[
            const SizedBox(
              height: 16,
              width: 16,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: AppColors.green,
              ),
            ),
            const SizedBox(height: 10),
          ],
          Text(
            text,
            style: const TextStyle(fontSize: 12, color: AppColors.muted),
          ),
          ?action,
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Add transaction page
// ---------------------------------------------------------------------------
class AddTransactionPage extends StatefulWidget {
  const AddTransactionPage({super.key, this.initialText});

  final String? initialText;

  @override
  State<AddTransactionPage> createState() => _AddTransactionPageState();
}

class _AddTransactionPageState extends State<AddTransactionPage> {
  final _formKey = GlobalKey<FormState>();
  final _amount = TextEditingController();
  final _category = TextEditingController();
  final _description = TextEditingController();

  static const _suggestions = <String>[
    'Food',
    'Transport',
    'Shopping',
    'Bills',
    'Health',
    'Entertainment',
    'Salary',
    'Other',
  ];

  String _type = 'expense';
  DateTime _date = DateTime.now();
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    final spoken = widget.initialText?.trim();
    if (spoken != null && spoken.isNotEmpty) {
      _description.text = spoken;
      final amount = RegExp(
        r'\d[\d,]*(?:\.\d{1,2})?',
      ).firstMatch(spoken.replaceAll(',', ''))?.group(0);
      if (amount != null) _amount.text = amount;
      if (RegExp(
        r'\b(income|salary|received|earned|deposit|deposited)\b|استلمت|اودعت|أودعت|راتب|مرتب',
        caseSensitive: false,
      ).hasMatch(spoken)) {
        _type = 'income';
      }
      final lower = spoken.toLowerCase();
      if (lower.contains('food') ||
          lower.contains('coffee') ||
          lower.contains('restaurant') ||
          lower.contains('مطعم') ||
          lower.contains('قهوة')) {
        _category.text = 'Food';
      } else if (lower.contains('taxi') ||
          lower.contains('uber') ||
          lower.contains('transport') ||
          lower.contains('تاكسي') ||
          lower.contains('مواصل')) {
        _category.text = 'Transport';
      } else if (lower.contains('bill') ||
          lower.contains('recharge') ||
          lower.contains('فاتورة') ||
          lower.contains('شحن')) {
        _category.text = 'Bills';
      } else if (lower.contains('salary') ||
          lower.contains('راتب') ||
          lower.contains('مرتب')) {
        _category.text = 'Salary';
      } else if (lower.contains('shop') ||
          lower.contains('amazon') ||
          lower.contains('شراء') ||
          lower.contains('تسوق')) {
        _category.text = 'Shopping';
      } else if (lower.contains('pharmacy') ||
          lower.contains('صيدلية') ||
          lower.contains('مستشفى')) {
        _category.text = 'Health';
      } else {
        _category.text = 'Other';
      }
    }
    _category.addListener(_onCategoryChanged);
  }

  @override
  void dispose() {
    _category.removeListener(_onCategoryChanged);
    _amount.dispose();
    _category.dispose();
    _description.dispose();
    super.dispose();
  }

  void _onCategoryChanged() {
    if (mounted) setState(() {});
  }

  Future<void> _pickDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _date,
      firstDate: DateTime(2000),
      lastDate: DateTime.now().add(const Duration(days: 365)),
      builder: (context, child) {
        return Theme(
          data: Theme.of(context).copyWith(
            colorScheme: const ColorScheme.dark(
              primary: AppColors.green,
              onPrimary: AppColors.onGreen,
              surface: AppColors.bgTop,
            ),
          ),
          child: child!,
        );
      },
    );

    if (picked != null) {
      setState(() {
        _date = DateTime(
          picked.year,
          picked.month,
          picked.day,
          _date.hour,
          _date.minute,
        );
      });
    }
  }

  Future<void> _submit() async {
    if (_saving) return;
    if (!(_formKey.currentState?.validate() ?? false)) return;

    setState(() => _saving = true);

    try {
      await Api.createTransaction(
        amount: _amount.text.trim(),
        category: _category.text.trim(),
        type: _type,
        description: _description.text.trim().isEmpty
            ? null
            : _description.text.trim(),
        date: _date,
      );

      if (!mounted) return;
      Navigator.of(context).pop(true);
    } catch (error) {
      if (!mounted) return;
      setState(() => _saving = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('$error'), backgroundColor: AppColors.red),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgBottom,
      appBar: AppBar(
        backgroundColor: AppColors.bgTop,
        title: const Text('New Transaction'),
      ),
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [AppColors.bgTop, AppColors.bgBottom],
          ),
        ),
        child: Form(
          key: _formKey,
          child: ListView(
            padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
            children: [
              Text(
                'Sending to ${ApiConfig.normalized}',
                style: const TextStyle(fontSize: 11, color: AppColors.muted),
              ),
              const SizedBox(height: 18),
              const Text(
                'Amount',
                style: TextStyle(fontSize: 13, color: Colors.white70),
              ),
              const SizedBox(height: 6),
              TextFormField(
                controller: _amount,
                keyboardType: const TextInputType.numberWithOptions(
                  decimal: true,
                ),
                style: const TextStyle(
                  fontSize: 32,
                  fontWeight: FontWeight.w800,
                ),
                decoration: InputDecoration(
                  hintText: '0.00',
                  hintStyle: const TextStyle(color: Colors.white24),
                  prefixText: 'EGP ',
                  prefixStyle: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                    color: AppColors.green,
                  ),
                  filled: true,
                  fillColor: AppColors.panel,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                    borderSide: BorderSide.none,
                  ),
                ),
                validator: (value) {
                  final parsed = double.tryParse((value ?? '').trim());
                  if (parsed == null || parsed <= 0) {
                    return 'Enter an amount greater than 0';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 18),
              const Text(
                'Type',
                style: TextStyle(fontSize: 13, color: Colors.white70),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: _TypeOption(
                      label: 'Expense',
                      icon: Icons.north_east_rounded,
                      color: AppColors.red,
                      selected: _type == 'expense',
                      onTap: () => setState(() => _type = 'expense'),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: _TypeOption(
                      label: 'Income',
                      icon: Icons.south_west_rounded,
                      color: AppColors.chartGreen,
                      selected: _type == 'income',
                      onTap: () => setState(() => _type = 'income'),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: _TypeOption(
                      label: 'Transfer',
                      icon: Icons.swap_horiz_rounded,
                      color: AppColors.gold,
                      selected: _type == 'transfer',
                      onTap: () => setState(() => _type = 'transfer'),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 18),
              const Text(
                'Category',
                style: TextStyle(fontSize: 13, color: Colors.white70),
              ),
              const SizedBox(height: 6),
              TextFormField(
                controller: _category,
                textCapitalization: TextCapitalization.words,
                style: const TextStyle(fontSize: 15),
                decoration: _inputDecoration(
                  hint: 'e.g. Food, Salary, Rent',
                  icon: Icons.category_outlined,
                ),
                validator: (value) {
                  if ((value ?? '').trim().isEmpty) {
                    return 'Choose or type a category';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 10),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: [
                  for (final suggestion in _suggestions)
                    ChoiceChip(
                      label: Text(suggestion),
                      labelStyle: TextStyle(
                        fontSize: 11,
                        color: _category.text == suggestion
                            ? AppColors.onGreen
                            : Colors.white70,
                      ),
                      selected: _category.text == suggestion,
                      selectedColor: AppColors.green,
                      backgroundColor: AppColors.panel,
                      side: BorderSide(
                        color: _category.text == suggestion
                            ? AppColors.green
                            : Colors.white24,
                      ),
                      onSelected: (_) {
                        _category.text = suggestion;
                        _category.selection = TextSelection.collapsed(
                          offset: suggestion.length,
                        );
                      },
                    ),
                ],
              ),
              const SizedBox(height: 18),
              const Text(
                'Date',
                style: TextStyle(fontSize: 13, color: Colors.white70),
              ),
              const SizedBox(height: 6),
              InkWell(
                borderRadius: BorderRadius.circular(12),
                onTap: _pickDate,
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 14,
                    vertical: 16,
                  ),
                  decoration: BoxDecoration(
                    color: AppColors.panel,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    children: [
                      const Icon(
                        Icons.event_outlined,
                        size: 20,
                        color: AppColors.muted,
                      ),
                      const SizedBox(width: 10),
                      Text(
                        formatDate(_date),
                        style: const TextStyle(fontSize: 14),
                      ),
                      const Spacer(),
                      const Icon(Icons.chevron_right, color: AppColors.muted),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 18),
              const Text(
                'Note (optional)',
                style: TextStyle(fontSize: 13, color: Colors.white70),
              ),
              const SizedBox(height: 6),
              TextFormField(
                controller: _description,
                maxLength: 255,
                maxLines: 2,
                decoration:
                    _inputDecoration(
                      hint: 'What was this for?',
                      icon: Icons.notes_outlined,
                    ).copyWith(
                      counterStyle: const TextStyle(
                        fontSize: 10,
                        color: AppColors.muted,
                      ),
                    ),
              ),
              const SizedBox(height: 8),
              SizedBox(
                height: 52,
                child: FilledButton(
                  onPressed: _saving ? null : _submit,
                  style: FilledButton.styleFrom(
                    backgroundColor: AppColors.green,
                    foregroundColor: AppColors.onGreen,
                    disabledBackgroundColor: AppColors.green.withAlpha(90),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  child: _saving
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(
                            strokeWidth: 2.5,
                            color: AppColors.onGreen,
                          ),
                        )
                      : const Text(
                          'Save Transaction',
                          style: TextStyle(
                            fontSize: 15,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  InputDecoration _inputDecoration({
    required String hint,
    required IconData icon,
  }) {
    return InputDecoration(
      hintText: hint,
      hintStyle: const TextStyle(color: Colors.white30),
      prefixIcon: Icon(icon, size: 20, color: AppColors.muted),
      filled: true,
      fillColor: AppColors.panel,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide.none,
      ),
    );
  }
}

class _TypeOption extends StatelessWidget {
  const _TypeOption({
    required this.label,
    required this.icon,
    required this.color,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final IconData icon;
  final Color color;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: selected ? color : AppColors.panel,
      borderRadius: BorderRadius.circular(10),
      child: InkWell(
        borderRadius: BorderRadius.circular(10),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 10),
          child: Column(
            children: [
              Icon(icon, size: 20, color: selected ? AppColors.onGreen : color),
              const SizedBox(height: 4),
              Text(
                label,
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  color: selected ? AppColors.onGreen : Colors.white70,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// SMS history page
// ---------------------------------------------------------------------------
class SmsHistoryPage extends StatefulWidget {
  const SmsHistoryPage({super.key});

  @override
  State<SmsHistoryPage> createState() => _SmsHistoryPageState();
}

class _SmsHistoryPageState extends State<SmsHistoryPage>
    with SingleTickerProviderStateMixin {
  late final TabController _tabs = TabController(length: 2, vsync: this);

  List<DeviceSms> _device = [];
  List<Map<String, dynamic>> _server = [];

  bool _loading = true;
  bool _permissionDenied = false;
  bool _deviceSupported = true;
  bool _syncing = false;
  bool _live = false;
  int _pending = 0;

  String? _deviceError;
  String? _serverError;

  StreamSubscription<SmsLiveEvent>? _liveSub;

  @override
  void initState() {
    super.initState();
    _listenLive();
    _load();
  }

  @override
  void dispose() {
    _liveSub?.cancel();
    _tabs.dispose();
    super.dispose();
  }

  void _listenLive() {
    try {
      _liveSub = SmsLive.stream.listen(
        _onLiveEvent,
        onError: (Object _) {},
        cancelOnError: false,
      );
    } catch (_) {
      // Live capture is Android-only; the rest of the page still works.
    }
  }

  void _onLiveEvent(SmsLiveEvent event) {
    if (!mounted) return;

    switch (event.type) {
      case 'received':
        final date = event.date == null
            ? DateTime.now()
            : DateTime.fromMillisecondsSinceEpoch(event.date! * 1000);
        setState(() {
          _device = [
            DeviceSms(
              id: DateTime.now().microsecondsSinceEpoch,
              sender: event.sender ?? 'Unknown',
              message: event.message ?? '',
              date: date,
            ),
            ..._device,
          ];
          _permissionDenied = false;
          _deviceSupported = true;
        });
        _showSnack(
          'New SMS from ${event.sender ?? 'Unknown'} — sending to server…',
          AppColors.green,
        );
        break;

      case 'synced':
        setState(() => _pending = event.pending);
        if (event.stored > 0) _loadServer();
        if (event.transactionsCreated > 0) {
          _showSnack(
            event.transactionsCreated == 1
                ? 'Transaction added from the new SMS.'
                : '${event.transactionsCreated} transactions added from the new SMS.',
            AppColors.chartGreen,
          );
        }
        break;

      case 'sync_failed':
        setState(() => _pending = event.pending);
        _showSnack(
          'SMS kept on the phone, waiting to sync. ${event.error ?? ''}'.trim(),
          AppColors.red,
          action: _settingsAction(),
        );
        break;

      case 'queue_flushed':
        setState(() => _pending = event.pending);
        if (event.pending == 0) _loadServer();
        if (event.transactionsCreated > 0) {
          _showSnack(
            event.transactionsCreated == 1
                ? 'Transaction added from a queued SMS.'
                : '${event.transactionsCreated} transactions added from queued SMS.',
            AppColors.chartGreen,
          );
        }
        break;
    }
  }

  SnackBarAction _settingsAction() {
    return SnackBarAction(
      label: 'Settings',
      textColor: Colors.white,
      onPressed: () {
        Navigator.of(
          context,
        ).push(MaterialPageRoute(builder: (_) => const SettingsPage()));
      },
    );
  }

  void _showSnack(String text, Color color, {SnackBarAction? action}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(text), backgroundColor: color, action: action),
    );
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _deviceError = null;
      _serverError = null;
    });

    await Future.wait([_loadDevice(), _loadServer()]);

    if (!mounted) return;
    setState(() => _loading = false);

    await _flushPending();
  }

  Future<void> _flushPending() async {
    try {
      final result = await SmsReader.flushPending();
      if (!mounted) return;
      setState(() => _pending = result.pending);
      if (result.stored > 0) await _loadServer();
    } catch (_) {
      // Not supported on this platform.
    }
  }

  Future<void> _loadDevice() async {
    try {
      var status = await SmsReader.permissionStatus();

      if (!status.canRead) {
        await SmsReader.requestPermission();
        status = await SmsReader.permissionStatus();
      }

      if (!mounted) return;

      if (!status.canRead) {
        setState(() {
          _permissionDenied = true;
          _deviceSupported = true;
          _live = status.canReceive;
        });
        return;
      }

      final messages = await SmsReader.readInbox(limit: 200);
      if (!mounted) return;
      setState(() {
        _device = messages;
        _permissionDenied = false;
        _deviceSupported = true;
        _live = status.canReceive;
      });
    } on MissingPluginException {
      if (!mounted) return;
      setState(() => _deviceSupported = false);
    } on PlatformException catch (error) {
      if (!mounted) return;
      if (error.code == 'permission_denied') {
        setState(() => _permissionDenied = true);
      } else {
        setState(() => _deviceError = error.message ?? error.code);
      }
    } catch (error) {
      if (!mounted) return;
      setState(() => _deviceError = '$error');
    }
  }

  Future<void> _loadServer() async {
    try {
      final items = await Api.fetchSmsHistory(limit: 200);
      if (!mounted) return;
      setState(() {
        _server = items;
        _serverError = null;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() => _serverError = '$error');
    }
  }

  Future<void> _syncToServer() async {
    if (_syncing || _device.isEmpty) return;

    setState(() => _syncing = true);

    try {
      final result = await Api.syncSms([
        for (final message in _device)
          {
            'sender': message.sender,
            'message': message.message,
            'date': message.date.millisecondsSinceEpoch ~/ 1000,
          },
      ]);

      if (!mounted) return;
      setState(() => _syncing = false);
      _tabs.animateTo(1);

      final created = (result['transactions_created'] as num?)?.toInt() ?? 0;
      final transactionsText = created > 0
          ? ', $created transaction${created == 1 ? '' : 's'} added'
          : '';

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Synced: ${result['stored']} new, '
            '${result['skipped']} already on the server$transactionsText',
          ),
          backgroundColor: AppColors.chartGreen,
        ),
      );

      await _loadServer();
    } catch (error) {
      if (!mounted) return;
      setState(() => _syncing = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('$error'),
          backgroundColor: AppColors.red,
          action: SnackBarAction(
            label: 'Settings',
            textColor: Colors.white,
            onPressed: () {
              Navigator.of(
                context,
              ).push(MaterialPageRoute(builder: (_) => const SettingsPage()));
            },
          ),
        ),
      );
    }
  }

  Future<void> _requestPermissionAgain() async {
    setState(() => _loading = true);
    await _loadDevice();
    if (!mounted) return;
    setState(() => _loading = false);
  }

  Future<void> _enableLive() async {
    try {
      await SmsReader.requestPermission();
      final status = await SmsReader.permissionStatus();
      if (!mounted) return;

      setState(() => _live = status.canReceive);

      if (status.canReceive) {
        _showSnack(
          'Live sync is on. New SMS are sent automatically.',
          AppColors.chartGreen,
        );
        await _flushPending();
      } else {
        _showSnack(
          'Receiving SMS is blocked. Allow the SMS permissions in app settings.',
          AppColors.red,
          action: SnackBarAction(
            label: 'Open settings',
            textColor: Colors.white,
            onPressed: () => SmsReader.openSettings(),
          ),
        );
      }
    } catch (error) {
      if (!mounted) return;
      _showSnack('$error', AppColors.red);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgBottom,
      appBar: AppBar(
        backgroundColor: AppColors.bgTop,
        title: const Text('SMS Tracking History'),
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: _loading ? null : _load,
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
        bottom: TabBar(
          controller: _tabs,
          isScrollable: true,
          tabAlignment: TabAlignment.start,
          indicatorColor: AppColors.green,
          labelColor: AppColors.green,
          unselectedLabelColor: Colors.white60,
          tabs: [
            Tab(text: 'On this phone (${_device.length})'),
            Tab(text: 'Synced (${_server.length})'),
          ],
        ),
      ),
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [AppColors.bgTop, AppColors.bgBottom],
          ),
        ),
        child: TabBarView(
          controller: _tabs,
          children: [_buildDeviceTab(), _buildServerTab()],
        ),
      ),
    );
  }

  Widget _buildDeviceTab() {
    if (_loading) return _loadingView();

    if (!_deviceSupported) {
      return _messageList([
        const _PanelMessage(
          text:
              'Reading the phone inbox is only available in the Android app.\n\n'
              'The "Synced" tab still shows messages stored on the backend.',
        ),
      ]);
    }

    if (_permissionDenied) {
      return _messageList([
        _PanelMessage(
          text:
              'SMS permission is needed to read the inbox.\n\n'
              'Tap "Allow SMS access". If Android no longer shows the prompt, '
              'open the app settings and enable the SMS permission manually.',
          action: Wrap(
            spacing: 8,
            children: [
              TextButton(
                onPressed: _requestPermissionAgain,
                child: const Text('Allow SMS access'),
              ),
              TextButton(
                onPressed: () => SmsReader.openSettings(),
                child: const Text('Open settings'),
              ),
            ],
          ),
        ),
      ]);
    }

    if (_deviceError != null) {
      return _messageList([
        _PanelMessage(
          text: _deviceError!,
          action: TextButton(onPressed: _load, child: const Text('Retry')),
        ),
      ]);
    }

    if (_device.isEmpty) {
      return _messageList([
        const _PanelMessage(
          text:
              'No SMS found in the phone inbox yet.\n\n'
              'Turn on live sync and new messages will appear here and be '
              'sent to the server automatically.',
        ),
      ]);
    }

    return RefreshIndicator(
      color: AppColors.green,
      backgroundColor: AppColors.bgTop,
      onRefresh: _load,
      child: ListView.builder(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
        itemCount: _device.length + 1,
        itemBuilder: (context, index) {
          if (index == 0) {
            return Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: _SyncCard(
                count: _device.length,
                syncing: _syncing,
                live: _live,
                pending: _pending,
                onSync: _syncToServer,
                onEnableLive: _enableLive,
              ),
            );
          }

          final message = _device[index - 1];
          return Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: _SmsTile(
              sender: message.sender,
              body: message.message,
              date: message.date,
            ),
          );
        },
      ),
    );
  }

  Widget _buildServerTab() {
    if (_loading) return _loadingView();

    if (_serverError != null) {
      return _messageList([
        _PanelMessage(
          text: _serverError!,
          action: Wrap(
            spacing: 8,
            children: [
              TextButton(onPressed: _load, child: const Text('Retry')),
              TextButton(
                onPressed: () {
                  Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => const SettingsPage()),
                  );
                },
                child: const Text('Server settings'),
              ),
            ],
          ),
        ),
      ]);
    }

    if (_server.isEmpty) {
      return _messageList([
        const _PanelMessage(
          text:
              'Nothing synced yet.\n\n'
              'Open the "On this phone" tab and tap "Sync to server", '
              'or run the Termux script against /api/sms/filter.',
        ),
      ]);
    }

    return RefreshIndicator(
      color: AppColors.green,
      backgroundColor: AppColors.bgTop,
      onRefresh: _load,
      child: ListView.builder(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
        itemCount: _server.length + 1,
        itemBuilder: (context, index) {
          if (index == 0) {
            return Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Text(
                'Stored on ${ApiConfig.normalized}',
                style: const TextStyle(fontSize: 11, color: AppColors.muted),
              ),
            );
          }

          final message = _server[index - 1];
          final transactionId = (message['transaction_id'] as num?)?.toInt();
          final badge = transactionId == null
              ? null
              : 'Transaction: ${message['transaction_currency'] ?? 'EGP'} '
                    '${message['transaction_amount'] ?? ''}'
                    ' · ${message['transaction_category'] ?? 'Other'}';

          return Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: _SmsTile(
              sender: '${message['sender'] ?? 'Unknown'}',
              body: '${message['message'] ?? ''}',
              date: parseDate(message['received_at']),
              badge: badge,
            ),
          );
        },
      ),
    );
  }

  Widget _loadingView() {
    return const Center(
      child: CircularProgressIndicator(color: AppColors.green),
    );
  }

  Widget _messageList(List<Widget> children) {
    return RefreshIndicator(
      color: AppColors.green,
      backgroundColor: AppColors.bgTop,
      onRefresh: _load,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
        children: children,
      ),
    );
  }
}

class _SyncCard extends StatelessWidget {
  const _SyncCard({
    required this.count,
    required this.syncing,
    required this.live,
    required this.pending,
    required this.onSync,
    required this.onEnableLive,
  });

  final int count;
  final bool syncing;
  final bool live;
  final int pending;
  final VoidCallback onSync;
  final VoidCallback onEnableLive;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.panel,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: (live ? AppColors.green : AppColors.muted).withAlpha(60),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                live ? Icons.sensors : Icons.sensors_off,
                size: 16,
                color: live ? AppColors.green : AppColors.muted,
              ),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  live
                      ? 'Live sync is on — new SMS are sent automatically.'
                      : 'Live sync is off — turn it on to capture new SMS.',
                  style: TextStyle(
                    fontSize: 11,
                    color: live ? AppColors.green : AppColors.muted,
                  ),
                ),
              ),
              if (!live)
                TextButton(
                  onPressed: onEnableLive,
                  style: TextButton.styleFrom(
                    visualDensity: VisualDensity.compact,
                    padding: const EdgeInsets.symmetric(horizontal: 8),
                  ),
                  child: const Text('Turn on'),
                ),
            ],
          ),
          if (pending > 0) ...[
            const SizedBox(height: 6),
            Text(
              '$pending message(s) waiting to sync.',
              style: const TextStyle(fontSize: 11, color: AppColors.red),
            ),
          ],
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: Text(
                  '$count messages found in the phone inbox.',
                  style: const TextStyle(fontSize: 12, color: AppColors.muted),
                ),
              ),
              const SizedBox(width: 8),
              FilledButton.icon(
                onPressed: syncing ? null : onSync,
                style: FilledButton.styleFrom(
                  backgroundColor: AppColors.green,
                  foregroundColor: AppColors.onGreen,
                  disabledBackgroundColor: AppColors.green.withAlpha(90),
                  visualDensity: VisualDensity.compact,
                ),
                icon: syncing
                    ? const SizedBox(
                        width: 14,
                        height: 14,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: AppColors.onGreen,
                        ),
                      )
                    : const Icon(Icons.cloud_upload_outlined, size: 16),
                label: Text(syncing ? 'Syncing…' : 'Sync to server'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _SmsTile extends StatelessWidget {
  const _SmsTile({
    required this.sender,
    required this.body,
    required this.date,
    this.badge,
  });

  final String sender;
  final String body;
  final DateTime? date;

  /// Shown when the backend turned this SMS into a transaction.
  final String? badge;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.panel,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 38,
            height: 38,
            decoration: BoxDecoration(
              color: AppColors.green.withAlpha(30),
              borderRadius: BorderRadius.circular(9),
            ),
            child: const Icon(
              Icons.sms_outlined,
              color: AppColors.green,
              size: 20,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        sender,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    if (date != null)
                      Text(
                        formatDate(date),
                        style: const TextStyle(
                          fontSize: 10,
                          color: AppColors.muted,
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  body,
                  style: const TextStyle(
                    fontSize: 12,
                    color: Colors.white70,
                    height: 1.35,
                  ),
                ),
                if (badge != null) ...[
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: AppColors.chartGreen.withAlpha(30),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(
                          Icons.check_circle_outline,
                          size: 12,
                          color: AppColors.chartGreen,
                        ),
                        const SizedBox(width: 4),
                        Flexible(
                          child: Text(
                            badge!,
                            style: const TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.w600,
                              color: AppColors.chartGreen,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Settings page (backend URL)
// ---------------------------------------------------------------------------
class SettingsPage extends StatefulWidget {
  const SettingsPage({super.key});

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  late final TextEditingController _url = TextEditingController(
    text: ApiConfig.baseUrl,
  );

  bool _testing = false;
  String? _testResult;
  bool _testOk = false;

  @override
  void dispose() {
    _url.dispose();
    super.dispose();
  }

  Future<void> _testConnection() async {
    setState(() {
      _testing = true;
      _testResult = null;
    });

    try {
      final items = await Api.fetchTransactions(limit: 1);
      if (!mounted) return;
      setState(() {
        _testing = false;
        _testOk = true;
        _testResult =
            'Connected. Server returned ${items.length} transaction(s).';
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _testing = false;
        _testOk = false;
        _testResult = '$error';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgBottom,
      appBar: AppBar(
        backgroundColor: AppColors.bgTop,
        title: const Text('Settings'),
      ),
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [AppColors.bgTop, AppColors.bgBottom],
          ),
        ),
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
          children: [
            const Text(
              'Backend server',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 6),
            const Text(
              'Android emulator: http://10.0.2.2:8000\n'
              'Real phone: use your PC LAN IP, e.g. http://192.168.1.10:8000 '
              '(run "ipconfig" on the PC). Phone and PC must be on the same Wi-Fi.',
              style: TextStyle(
                fontSize: 11,
                color: AppColors.muted,
                height: 1.5,
              ),
            ),
            const SizedBox(height: 14),
            TextField(
              controller: _url,
              keyboardType: TextInputType.url,
              autocorrect: false,
              decoration: InputDecoration(
                hintText: 'http://192.168.1.10:8000',
                prefixIcon: const Icon(
                  Icons.dns_outlined,
                  size: 20,
                  color: AppColors.muted,
                ),
                filled: true,
                fillColor: AppColors.panel,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide.none,
                ),
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: FilledButton(
                    onPressed: () {
                      _saveServerUrl();
                    },
                    style: FilledButton.styleFrom(
                      backgroundColor: AppColors.green,
                      foregroundColor: AppColors.onGreen,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10),
                      ),
                    ),
                    child: const Text('Save'),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: OutlinedButton(
                    onPressed: _testing ? null : _testConnection,
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.white,
                      side: const BorderSide(color: Colors.white54),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10),
                      ),
                    ),
                    child: _testing
                        ? const SizedBox(
                            height: 16,
                            width: 16,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: AppColors.green,
                            ),
                          )
                        : const Text('Test'),
                  ),
                ),
              ],
            ),
            if (_testResult != null) ...[
              const SizedBox(height: 14),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppColors.panel,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: (_testOk ? AppColors.green : AppColors.red)
                        .withAlpha(120),
                  ),
                ),
                child: Text(
                  _testResult!,
                  style: TextStyle(
                    fontSize: 11,
                    height: 1.4,
                    color: _testOk ? AppColors.green : AppColors.red,
                  ),
                ),
              ),
            ],
            const SizedBox(height: 28),
            const Text(
              'Current URL',
              style: TextStyle(fontSize: 12, color: AppColors.muted),
            ),
            const SizedBox(height: 4),
            Text(
              ApiConfig.normalized,
              style: const TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w700,
                color: Colors.white70,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _saveServerUrl() async {
    final enteredValue = _url.text.trim().replaceFirst(RegExp(r'/+$'), '');
    final uri = Uri.tryParse(enteredValue);
    if (uri == null ||
        !uri.hasAuthority ||
        (uri.scheme != 'http' && uri.scheme != 'https')) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Enter a valid http:// or https:// server URL'),
          backgroundColor: AppColors.red,
        ),
      );
      return;
    }

    final value = uri
        .replace(
          scheme: uri.scheme == 'https' && ApiConfig._isLocalHost(uri.host)
              ? 'http'
              : uri.scheme,
        )
        .toString()
        .replaceFirst(RegExp(r'/+$'), '');

    final preferences = await SharedPreferences.getInstance();
    await preferences.setString(_backendUrlPreference, value);
    ApiConfig.baseUrl = value;
    if (!mounted) return;
    setState(() {});
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Server URL saved'),
        backgroundColor: AppColors.chartGreen,
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Line chart (no external package)
// ---------------------------------------------------------------------------
class _LineChartPainter extends CustomPainter {
  _LineChartPainter({required this.values, required this.labels});

  final List<double> values;
  final List<String> labels;
  static const double maxY = 400;

  void _text(Canvas c, String s, Offset anchor, {required bool rightAligned}) {
    final tp = TextPainter(
      text: TextSpan(
        text: s,
        style: const TextStyle(color: AppColors.muted, fontSize: 10),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    final dx = rightAligned ? anchor.dx - tp.width : anchor.dx - tp.width / 2;
    final dy = rightAligned ? anchor.dy - tp.height / 2 : anchor.dy;
    tp.paint(c, Offset(dx, dy));
  }

  @override
  void paint(Canvas canvas, Size size) {
    const left = 40.0, right = 14.0, top = 14.0, bottom = 28.0;
    final plot = Rect.fromLTRB(
      left,
      top,
      size.width - right,
      size.height - bottom,
    );

    // Grid + y labels
    final grid = Paint()
      ..color = Colors.white.withAlpha(110)
      ..strokeWidth = 1;
    for (var v = 0; v <= maxY; v += 100) {
      final y = plot.bottom - (v / maxY) * plot.height;
      canvas.drawLine(Offset(plot.left, y), Offset(plot.right, y), grid);
      _text(canvas, '$v', Offset(plot.left - 8, y), rightAligned: true);
    }

    // Data points
    final n = values.length;
    final pts = <Offset>[
      for (var i = 0; i < n; i++)
        Offset(
          plot.left + plot.width * i / (n - 1),
          plot.bottom - (values[i] / maxY) * plot.height,
        ),
    ];

    // Smooth curve (horizontal control points => no overshoot)
    final line = Path()..moveTo(pts.first.dx, pts.first.dy);
    for (var i = 0; i < pts.length - 1; i++) {
      final a = pts[i], b = pts[i + 1];
      final mx = (a.dx + b.dx) / 2;
      line.cubicTo(mx, a.dy, mx, b.dy, b.dx, b.dy);
    }

    // Gradient fill under the curve
    final fill = Path.from(line)
      ..lineTo(pts.last.dx, plot.bottom)
      ..lineTo(pts.first.dx, plot.bottom)
      ..close();
    canvas.drawPath(
      fill,
      Paint()
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            AppColors.chartGreen.withAlpha(150),
            AppColors.chartGreen.withAlpha(12),
          ],
        ).createShader(plot),
    );

    // Stroke
    canvas.drawPath(
      line,
      Paint()
        ..color = AppColors.chartGreen
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2
        ..strokeJoin = StrokeJoin.round
        ..strokeCap = StrokeCap.round,
    );

    // x labels
    for (var i = 0; i < n; i++) {
      _text(
        canvas,
        labels[i],
        Offset(pts[i].dx, plot.bottom + 8),
        rightAligned: false,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _LineChartPainter old) =>
      old.values != values || old.labels != labels;
}

// ---------------------------------------------------------------------------
// Bottom navigation with floating voice button
// ---------------------------------------------------------------------------
class _BottomNav extends StatelessWidget {
  const _BottomNav({
    required this.index,
    required this.onTab,
    required this.onVoice,
  });

  final int index;
  final ValueChanged<int> onTab;
  final VoidCallback onVoice;

  @override
  Widget build(BuildContext context) {
    final bottomInset = MediaQuery.of(context).padding.bottom;
    return Container(
      height: 104 + bottomInset,
      padding: EdgeInsets.fromLTRB(12, 0, 12, 12 + bottomInset),
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color(0x00062228), Color(0xF2062228)],
          stops: [0.0, 0.35],
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          _NavItem(
            icon: Icons.home_rounded,
            label: 'Home',
            selected: index == 0,
            onTap: () => onTab(0),
          ),
          _NavItem(
            icon: Icons.show_chart_rounded,
            label: 'Insights',
            selected: index == 1,
            onTap: () => onTab(1),
          ),
          _VoiceButton(onTap: onVoice),
          _NavItem(
            icon: Icons.multiline_chart_rounded,
            label: 'Wize',
            selected: index == 2,
            onTap: () => onTab(2),
          ),
          _NavItem(
            icon: Icons.settings_rounded,
            label: 'Settings',
            selected: index == 3,
            onTap: () => onTab(3),
          ),
        ],
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  const _NavItem({
    required this.icon,
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final color = selected ? AppColors.green : Colors.white;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(10),
      child: SizedBox(
        width: 62,
        height: 56,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.end,
          children: [
            Icon(icon, size: 26, color: color),
            const SizedBox(height: 2),
            Text(
              label,
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w700,
                color: color,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _VoiceButton extends StatelessWidget {
  const _VoiceButton({required this.onTap});
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: 'Record a transaction by voice',
      child: Tooltip(
        message: 'Record a transaction by voice',
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(36),
          child: SizedBox(
            width: 68,
            height: 76,
            child: Column(
              mainAxisAlignment: MainAxisAlignment.start,
              children: [
                Container(
                  width: 56,
                  height: 56,
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [AppColors.green, AppColors.chartGreen],
                    ),
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                        color: AppColors.green.withAlpha(60),
                        blurRadius: 14,
                        spreadRadius: 1,
                      ),
                    ],
                  ),
                  child: const Icon(
                    Icons.mic_rounded,
                    color: AppColors.onGreen,
                    size: 28,
                  ),
                ),
                const SizedBox(height: 2),
                const Text(
                  'Voice',
                  style: TextStyle(
                    fontSize: 10,
                    color: Colors.white,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Green speech-bubble: circle with a small tail at the lower right.
class _BubblePainter extends CustomPainter {
  const _BubblePainter();

  @override
  void paint(Canvas canvas, Size size) {
    const center = Offset(32, 32);
    const radius = 32.0;

    // soft glow
    canvas.drawCircle(
      center,
      radius,
      Paint()
        ..color = AppColors.green.withAlpha(90)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 12),
    );

    final paint = Paint()..color = AppColors.green;
    canvas.drawCircle(center, radius, paint);

    final tail = Path()
      ..moveTo(36, 61)
      ..lineTo(56, 46)
      ..lineTo(50, 68)
      ..close();
    canvas.drawPath(tail, paint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
