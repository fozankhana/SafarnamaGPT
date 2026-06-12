import 'source_doc.dart';

sealed class ChatEvent {}

class TokenEvent extends ChatEvent {
  final String value;
  TokenEvent(this.value);
}

class SourcesEvent extends ChatEvent {
  final List<SourceDoc> docs;
  SourcesEvent(this.docs);
}

class DoneEvent extends ChatEvent {}

class ErrorEvent extends ChatEvent {
  final String message;
  ErrorEvent(this.message);
}
