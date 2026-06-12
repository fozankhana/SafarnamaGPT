import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:uuid/uuid.dart';

import '../models/chat_event.dart';
import '../models/conversation.dart';
import '../models/source_doc.dart';
import '../services/api_service.dart';
import '../widgets/settings_sheet.dart';
import 'history_screen.dart';

const _starters = [
  "I'm planning a 7-day trip to Pakistan. Help me plan!",
  "Plan a 5-day trip to Lahore and Islamabad",
  "I want to trek in Gilgit-Baltistan for 10 days",
  "What are the best places to visit in Hunza Valley?",
  "Plan a cultural tour of historic cities in Pakistan",
  "I have 3 days in Karachi — what should I do?",
];

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _api = ApiService.instance;
  final _inputCtrl = TextEditingController();
  final _scrollCtrl = ScrollController();
  final _uuid = const Uuid();

  String _convId = const Uuid().v4();
  List<Message> _messages = [];
  List<SourceDoc> _sources = [];
  bool _streaming = false;
  String _streamingText = '';

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtrl.hasClients) {
        _scrollCtrl.animateTo(
          _scrollCtrl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _send(String text) async {
    if (text.trim().isEmpty || _streaming) return;
    _inputCtrl.clear();

    final userMsg = Message(role: 'user', content: text.trim());
    setState(() {
      _messages = [..._messages, userMsg];
      _streaming = true;
      _streamingText = '';
      _sources = [];
    });
    _scrollToBottom();

    final history = _messages.sublist(0, _messages.length - 1); // exclude current

    try {
      await for (final event in _api.streamChat(
        message: text.trim(),
        conversationId: _convId,
        history: history,
      )) {
        switch (event) {
          case TokenEvent(:final value):
            setState(() => _streamingText += value);
            _scrollToBottom();
          case SourcesEvent(:final docs):
            setState(() => _sources = docs);
          case DoneEvent():
            final assistantMsg = Message(role: 'assistant', content: _streamingText);
            final title = _messages.isEmpty ? text.trim() : _messages.first.content;
            final conv = Conversation(
              id: _convId,
              title: title.length > 45 ? '${title.substring(0, 45)}…' : title,
              updated: DateTime.now().toIso8601String(),
              messages: [..._messages, assistantMsg],
            );
            await _api.saveConversation(conv);
            setState(() {
              _messages = conv.messages;
              _streamingText = '';
              _streaming = false;
            });
          case ErrorEvent(:final message):
            setState(() {
              _streamingText = '';
              _streaming = false;
            });
            if (mounted) {
              ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $message'), backgroundColor: Colors.red));
            }
        }
      }
    } catch (e) {
      setState(() { _streaming = false; _streamingText = ''; });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Connection error: $e'), backgroundColor: Colors.red));
      }
    }
  }

  void _newChat() {
    setState(() {
      _convId = _uuid.v4();
      _messages = [];
      _sources = [];
      _streamingText = '';
      _streaming = false;
    });
  }

  Future<void> _openHistory() async {
    final conv = await Navigator.push<Conversation>(
      context,
      MaterialPageRoute(builder: (_) => const HistoryScreen()),
    );
    if (conv != null) {
      setState(() {
        _convId = conv.id;
        _messages = conv.messages;
        _sources = [];
        _streamingText = '';
        _streaming = false;
      });
    }
  }

  Future<void> _openSettings() async {
    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => const SettingsSheet(),
    );
  }

  @override
  void dispose() {
    _inputCtrl.dispose();
    _scrollCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final showStarters = _messages.isEmpty && !_streaming;

    return Scaffold(
      appBar: AppBar(
        title: const Text('🕌 SafarnāmaGPT'),
        centerTitle: true,
        actions: [
          IconButton(icon: const Icon(Icons.history), onPressed: _openHistory, tooltip: 'History'),
          IconButton(icon: const Icon(Icons.add_comment_outlined), onPressed: _newChat, tooltip: 'New chat'),
          IconButton(icon: const Icon(Icons.settings_outlined), onPressed: _openSettings, tooltip: 'Settings'),
        ],
      ),
      body: Column(
        children: [
          // ── Chat messages ──────────────────────────────────────────────────
          Expanded(
            child: ListView(
              controller: _scrollCtrl,
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              children: [
                // Welcome card
                if (showStarters) ...[
                  const SizedBox(height: 12),
                  Card(
                    color: cs.primaryContainer.withOpacity(0.4),
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('👋 Welcome to SafarnāmaGPT!', style: Theme.of(context).textTheme.titleMedium),
                          const SizedBox(height: 8),
                          const Text(
                            'Your AI travel agent for Pakistan. Tell me how many days you\'re '
                            'traveling and which regions interest you — I\'ll build a complete '
                            'day-by-day itinerary with Google Maps links!',
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text('Start planning:', style: Theme.of(context).textTheme.labelLarge),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8, runSpacing: 8,
                    children: _starters.map((q) => ActionChip(
                      label: Text(q, style: const TextStyle(fontSize: 12)),
                      onPressed: () => _send(q),
                    )).toList(),
                  ),
                  const SizedBox(height: 16),
                ],

                // Past messages
                for (final msg in _messages) _ChatBubble(message: msg),

                // Streaming bubble
                if (_streaming || _streamingText.isNotEmpty)
                  _ChatBubble(
                    message: Message(role: 'assistant', content: _streamingText),
                    isStreaming: _streaming && _streamingText.isEmpty,
                  ),

                // Sources panel
                if (_sources.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  _SourcesPanel(sources: _sources),
                ],

                const SizedBox(height: 8),
              ],
            ),
          ),

          // ── Input bar ──────────────────────────────────────────────────────
          Container(
            color: cs.surface,
            padding: EdgeInsets.fromLTRB(12, 8, 12, MediaQuery.of(context).viewInsets.bottom + 8),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _inputCtrl,
                    minLines: 1,
                    maxLines: 4,
                    textInputAction: TextInputAction.newline,
                    decoration: InputDecoration(
                      hintText: 'Tell me your travel plans…',
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(24)),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    ),
                    onSubmitted: _send,
                  ),
                ),
                const SizedBox(width: 8),
                FilledButton(
                  onPressed: _streaming ? null : () => _send(_inputCtrl.text),
                  style: FilledButton.styleFrom(
                    shape: const CircleBorder(),
                    padding: const EdgeInsets.all(14),
                  ),
                  child: _streaming
                      ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Icon(Icons.send),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _ChatBubble extends StatelessWidget {
  final Message message;
  final bool isStreaming;

  const _ChatBubble({required this.message, this.isStreaming = false});

  @override
  Widget build(BuildContext context) {
    final isUser = message.role == 'user';
    final cs = Theme.of(context).colorScheme;

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.85),
        decoration: BoxDecoration(
          color: isUser ? cs.primary : cs.surfaceContainerHigh,
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(18),
            topRight: const Radius.circular(18),
            bottomLeft: Radius.circular(isUser ? 18 : 4),
            bottomRight: Radius.circular(isUser ? 4 : 18),
          ),
        ),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        child: isStreaming
            ? Row(mainAxisSize: MainAxisSize.min, children: [
                SizedBox(
                  width: 16, height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2, color: cs.onSurfaceVariant),
                ),
                const SizedBox(width: 8),
                Text('Thinking…', style: TextStyle(color: cs.onSurfaceVariant)),
              ])
            : isUser
                ? Text(message.content, style: TextStyle(color: cs.onPrimary))
                : MarkdownBody(
                    data: message.content,
                    styleSheet: MarkdownStyleSheet.fromTheme(Theme.of(context)),
                    onTapLink: (_, href, __) async {
                      if (href != null) {
                        final uri = Uri.tryParse(href);
                        if (uri != null) await launchUrl(uri, mode: LaunchMode.externalApplication);
                      }
                    },
                  ),
      ),
    );
  }
}

class _SourcesPanel extends StatelessWidget {
  final List<SourceDoc> sources;
  const _SourcesPanel({required this.sources});

  @override
  Widget build(BuildContext context) => Card(
        margin: EdgeInsets.zero,
        child: ExpansionTile(
          leading: const Icon(Icons.library_books_outlined),
          title: Text('Sources (${sources.length})', style: const TextStyle(fontSize: 13)),
          children: sources.map((doc) => ListTile(
            dense: true,
            title: Text(doc.sourceLabel, style: const TextStyle(fontSize: 12)),
            subtitle: Text(doc.text.length > 120 ? '${doc.text.substring(0, 120)}…' : doc.text, style: const TextStyle(fontSize: 11)),
            trailing: Text('${doc.matchPercent}%', style: const TextStyle(fontSize: 11)),
            onTap: () async {
              final uri = Uri.tryParse(doc.sourceUrl);
              if (uri != null) await launchUrl(uri, mode: LaunchMode.externalApplication);
            },
          )).toList(),
        ),
      );
}
