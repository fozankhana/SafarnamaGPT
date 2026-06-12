import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import '../models/chat_event.dart';
import '../models/conversation.dart';
import '../models/source_doc.dart';

class ApiService {
  ApiService._();
  static final ApiService instance = ApiService._();

  static const _keyBaseUrl = 'base_url';
  static const _keyGroqKey = 'groq_api_key';
  static const _keyTemp = 'temperature';
  static const _keyTopK = 'retrieval_top_k';
  static const _keyMaxTokens = 'max_tokens';

  static const defaultBaseUrl = 'https://safarnamagpt-api.onrender.com';

  String _baseUrl = defaultBaseUrl;
  String _groqKey = '';
  double _temperature = 0.7;
  int _topK = 4;
  int _maxTokens = 2048;

  String get baseUrl => _baseUrl;
  String get groqKey => _groqKey;
  double get temperature => _temperature;
  int get topK => _topK;
  int get maxTokens => _maxTokens;

  Future<void> loadPrefs() async {
    final p = await SharedPreferences.getInstance();
    _baseUrl = p.getString(_keyBaseUrl) ?? defaultBaseUrl;
    _groqKey = p.getString(_keyGroqKey) ?? '';
    _temperature = p.getDouble(_keyTemp) ?? 0.7;
    _topK = p.getInt(_keyTopK) ?? 4;
    _maxTokens = p.getInt(_keyMaxTokens) ?? 2048;
  }

  Future<void> savePrefs({
    String? baseUrl,
    String? groqKey,
    double? temperature,
    int? topK,
    int? maxTokens,
  }) async {
    final p = await SharedPreferences.getInstance();
    if (baseUrl != null) { _baseUrl = baseUrl; await p.setString(_keyBaseUrl, baseUrl); }
    if (groqKey != null) { _groqKey = groqKey; await p.setString(_keyGroqKey, groqKey); }
    if (temperature != null) { _temperature = temperature; await p.setDouble(_keyTemp, temperature); }
    if (topK != null) { _topK = topK; await p.setInt(_keyTopK, topK); }
    if (maxTokens != null) { _maxTokens = maxTokens; await p.setInt(_keyMaxTokens, maxTokens); }
  }

  Stream<ChatEvent> streamChat({
    required String message,
    required String conversationId,
    required List<Message> history,
  }) async* {
    final uri = Uri.parse('$_baseUrl/chat/stream');
    final body = jsonEncode({
      'message': message,
      'conversation_id': conversationId,
      'history': history.map((m) => m.toJson()).toList(),
      'groq_api_key': _groqKey,
      'temperature': _temperature,
      'retrieval_top_k': _topK,
      'max_tokens': _maxTokens,
    });

    final request = http.Request('POST', uri)
      ..headers['Content-Type'] = 'application/json'
      ..headers['Accept'] = 'text/event-stream'
      ..body = body;

    final response = await http.Client().send(request);

    if (response.statusCode != 200) {
      yield ErrorEvent('Server error ${response.statusCode}');
      return;
    }

    final stream = response.stream.transform(utf8.decoder).transform(const LineSplitter());

    await for (final line in stream) {
      if (!line.startsWith('data: ')) continue;
      final payload = line.substring(6).trim();
      if (payload.isEmpty) continue;

      try {
        final json = jsonDecode(payload) as Map<String, dynamic>;
        final type = json['type'] as String;
        switch (type) {
          case 'token':
            yield TokenEvent(json['value'] as String? ?? '');
          case 'sources':
            final docs = (json['docs'] as List<dynamic>)
                .map((e) => SourceDoc.fromJson(e as Map<String, dynamic>))
                .toList();
            yield SourcesEvent(docs);
          case 'done':
            yield DoneEvent();
            return;
          case 'error':
            yield ErrorEvent(json['message'] as String? ?? 'Unknown error');
            return;
        }
      } catch (_) {
        continue;
      }
    }
    yield DoneEvent();
  }

  Future<List<Conversation>> getConversations() async {
    final resp = await http.get(Uri.parse('$_baseUrl/conversations'));
    if (resp.statusCode != 200) return [];
    final list = jsonDecode(resp.body) as List<dynamic>;
    return list.map((e) => Conversation.fromJson({'messages': [], ...e as Map<String, dynamic>})).toList();
  }

  Future<Conversation?> getConversation(String id) async {
    final resp = await http.get(Uri.parse('$_baseUrl/conversations/$id'));
    if (resp.statusCode != 200) return null;
    return Conversation.fromJson(jsonDecode(resp.body) as Map<String, dynamic>);
  }

  Future<void> saveConversation(Conversation conv) async {
    await http.post(
      Uri.parse('$_baseUrl/conversations/${conv.id}'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'title': conv.title, 'messages': conv.messages.map((m) => m.toJson()).toList()}),
    );
  }

  Future<void> deleteConversation(String id) async {
    await http.delete(Uri.parse('$_baseUrl/conversations/$id'));
  }
}
