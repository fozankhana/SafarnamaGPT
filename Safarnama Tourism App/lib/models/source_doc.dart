class SourceDoc {
  final String text;
  final String sourceLabel;
  final String sourceUrl;
  final double score;

  const SourceDoc({
    required this.text,
    required this.sourceLabel,
    required this.sourceUrl,
    required this.score,
  });

  factory SourceDoc.fromJson(Map<String, dynamic> j) => SourceDoc(
        text: j['text'] as String? ?? '',
        sourceLabel: j['source_label'] as String? ?? '',
        sourceUrl: j['source_url'] as String? ?? '',
        score: (j['score'] as num?)?.toDouble() ?? 0.0,
      );

  // L2 distance: lower = better. Convert to 0–100% match score.
  int get matchPercent {
    final pct = ((1.0 / (1.0 + score)) * 100).round();
    return pct.clamp(0, 100);
  }
}
