import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../models/conversation.dart';
import '../services/api_service.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  final _api = ApiService.instance;
  late Future<List<Conversation>> _future;

  @override
  void initState() {
    super.initState();
    _future = _api.getConversations();
  }

  String _formatDate(String iso) {
    if (iso.isEmpty) return '';
    try {
      final dt = DateTime.parse(iso);
      return DateFormat('d MMM y, HH:mm').format(dt);
    } catch (_) {
      return iso;
    }
  }

  Future<void> _delete(String id) async {
    await _api.deleteConversation(id);
    setState(() => _future = _api.getConversations());
  }

  Future<void> _open(String id) async {
    final conv = await _api.getConversation(id);
    if (conv != null && mounted) Navigator.pop(context, conv);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Chat History')),
        body: FutureBuilder<List<Conversation>>(
          future: _future,
          builder: (_, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            final convs = snap.data ?? [];
            if (convs.isEmpty) {
              return const Center(child: Text('No saved conversations yet.'));
            }
            return ListView.separated(
              itemCount: convs.length,
              separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (_, i) {
                final c = convs[i];
                return Dismissible(
                  key: Key(c.id),
                  direction: DismissDirection.endToStart,
                  background: Container(
                    color: Colors.red,
                    alignment: Alignment.centerRight,
                    padding: const EdgeInsets.only(right: 20),
                    child: const Icon(Icons.delete, color: Colors.white),
                  ),
                  onDismissed: (_) => _delete(c.id),
                  child: ListTile(
                    title: Text(c.title, maxLines: 1, overflow: TextOverflow.ellipsis),
                    subtitle: Text(_formatDate(c.updated), style: const TextStyle(fontSize: 12)),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => _open(c.id),
                  ),
                );
              },
            );
          },
        ),
      );
}
