/**
 * Handles streaming response from the backend (SSE).
 * @param {Response} response - The fetch response object.
 * @param {Function} onToken - Callback for new tokens.
 * @param {Function} onMetadata - Callback for metadata (sources, stats).
 * @param {Function} onError - Callback for errors.
 */
export async function handleStream(response, onToken, onMetadata, onError) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop(); // Keep partial line in buffer

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.error) {
              onError(data.error);
            } else if (data.sources || data.stats) {
              onMetadata(data);
            } else if (data.token) {
              onToken(data.token);
            }
          } catch (e) {
            console.error('Error parsing SSE line:', e);
          }
        }
      }
    }
  } catch (err) {
    onError(err.message);
  }
}
