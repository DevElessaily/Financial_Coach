/// Normalises speech text before extracting a transaction amount.
String normalizeVoiceTranscript(String transcript) {
  return transcript
      .replaceAllMapped(RegExp('[٠-٩۰-۹]'), (match) {
        final code = match.group(0)!.codeUnitAt(0);
        final digit = code >= 0x06F0 ? code - 0x06F0 : code - 0x0660;
        return '$digit';
      })
      .replaceAll(RegExp(r'\s+'), ' ')
      .trim();
}
