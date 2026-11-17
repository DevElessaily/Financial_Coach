/// Metadata for an optional, checksum-pinned Whisper model download.
///
/// This app's voice entry uses Android's speech service and does not bundle
/// Whisper models. Descriptors can be supplied by a host app if Whisper support
/// is added later.
final class WhisperModelDescriptor {
  const WhisperModelDescriptor({
    required this.name,
    required this.fileName,
    required this.uri,
    required this.sha256,
  });

  final String name;
  final String fileName;
  final Uri uri;
  final String sha256;
}
