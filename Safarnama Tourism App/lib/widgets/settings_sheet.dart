import 'package:flutter/material.dart';
import '../services/api_service.dart';

class SettingsSheet extends StatefulWidget {
  const SettingsSheet({super.key});

  @override
  State<SettingsSheet> createState() => _SettingsSheetState();
}

class _SettingsSheetState extends State<SettingsSheet> {
  final _api = ApiService.instance;
  late TextEditingController _keyCtrl;
  late TextEditingController _urlCtrl;
  late double _temperature;
  late int _topK;
  late int _maxTokens;

  @override
  void initState() {
    super.initState();
    _keyCtrl = TextEditingController(text: _api.groqKey);
    _urlCtrl = TextEditingController(text: _api.baseUrl);
    _temperature = _api.temperature;
    _topK = _api.topK;
    _maxTokens = _api.maxTokens;
  }

  @override
  void dispose() {
    _keyCtrl.dispose();
    _urlCtrl.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    await _api.savePrefs(
      groqKey: _keyCtrl.text.trim(),
      baseUrl: _urlCtrl.text.trim(),
      temperature: _temperature,
      topK: _topK,
      maxTokens: _maxTokens,
    );
    if (mounted) Navigator.pop(context, true);
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return DraggableScrollableSheet(
      initialChildSize: 0.75,
      minChildSize: 0.4,
      maxChildSize: 0.95,
      expand: false,
      builder: (_, scroll) => Container(
        decoration: BoxDecoration(
          color: cs.surface,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
        ),
        child: ListView(
          controller: scroll,
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
          children: [
            Center(
              child: Container(
                width: 40, height: 4,
                margin: const EdgeInsets.only(bottom: 16),
                decoration: BoxDecoration(color: cs.onSurfaceVariant.withOpacity(0.4), borderRadius: BorderRadius.circular(2)),
              ),
            ),
            Text('Settings', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 20),

            Text('Groq API Key', style: Theme.of(context).textTheme.labelLarge),
            const SizedBox(height: 6),
            TextField(
              controller: _keyCtrl,
              obscureText: true,
              decoration: InputDecoration(
                hintText: 'gsk_...',
                helperText: 'Get a free key at console.groq.com',
                border: const OutlineInputBorder(),
                suffixIcon: IconButton(icon: const Icon(Icons.clear), onPressed: () => _keyCtrl.clear()),
              ),
            ),
            const SizedBox(height: 16),

            Text('Backend URL', style: Theme.of(context).textTheme.labelLarge),
            const SizedBox(height: 6),
            TextField(
              controller: _urlCtrl,
              keyboardType: TextInputType.url,
              decoration: const InputDecoration(
                hintText: 'https://safarnamagpt-api.onrender.com',
                border: OutlineInputBorder(),
              ),
            ),
            const Divider(height: 32),

            _SliderRow(
              label: 'Temperature',
              value: _temperature,
              min: 0.1, max: 1.0, divisions: 18,
              display: _temperature.toStringAsFixed(2),
              onChanged: (v) => setState(() => _temperature = v),
            ),
            _SliderRow(
              label: 'Retrieved chunks (top-k)',
              value: _topK.toDouble(),
              min: 1, max: 8, divisions: 7,
              display: '$_topK',
              onChanged: (v) => setState(() => _topK = v.round()),
            ),
            _SliderRow(
              label: 'Max response tokens',
              value: _maxTokens.toDouble(),
              min: 256, max: 4096, divisions: 30,
              display: '$_maxTokens',
              onChanged: (v) => setState(() => _maxTokens = v.round()),
            ),
            const SizedBox(height: 24),

            FilledButton(onPressed: _save, child: const Text('Save')),
          ],
        ),
      ),
    );
  }
}

class _SliderRow extends StatelessWidget {
  final String label;
  final double value;
  final double min, max;
  final int divisions;
  final String display;
  final ValueChanged<double> onChanged;

  const _SliderRow({
    required this.label,
    required this.value,
    required this.min,
    required this.max,
    required this.divisions,
    required this.display,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Text(label, style: Theme.of(context).textTheme.labelLarge),
            const Spacer(),
            Text(display, style: Theme.of(context).textTheme.bodySmall),
          ]),
          Slider(value: value, min: min, max: max, divisions: divisions, onChanged: onChanged),
          const SizedBox(height: 8),
        ],
      );
}
