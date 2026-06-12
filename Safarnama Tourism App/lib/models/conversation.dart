class Message {
  final String role;
  final String content;

  const Message({required this.role, required this.content});

  factory Message.fromJson(Map<String, dynamic> j) =>
      Message(role: j['role'] as String, content: j['content'] as String);

  Map<String, dynamic> toJson() => {'role': role, 'content': content};
}

class Conversation {
  final String id;
  final String title;
  final String updated;
  final List<Message> messages;

  const Conversation({
    required this.id,
    required this.title,
    required this.updated,
    required this.messages,
  });

  factory Conversation.fromJson(Map<String, dynamic> j) => Conversation(
        id: j['id'] as String,
        title: j['title'] as String? ?? 'Untitled',
        updated: j['updated'] as String? ?? '',
        messages: (j['messages'] as List<dynamic>? ?? [])
            .map((e) => Message.fromJson(e as Map<String, dynamic>))
            .toList(),
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'title': title,
        'updated': updated,
        'messages': messages.map((m) => m.toJson()).toList(),
      };
}
