import { StyleSheet, Text } from 'react-native';

import { colors } from '@/theme';
import type { SaveSnapshot } from './autosaveQueue';

/** Subtle autosave status line. */
export function SaveIndicator({ save }: { save: SaveSnapshot }) {
  let text: string;
  let color: string = colors.textSubtle;
  if (save.status === 'retrying') {
    text = 'Not saved yet — retrying…';
    color = colors.warn700;
  } else if (save.status === 'error' && save.pending > 0) {
    text = 'Not saved — will try again';
    color = colors.warn700;
  } else if (save.status === 'saving' || save.pending > 0) {
    text = 'Saving…';
  } else {
    text = 'All answers saved';
    color = colors.trust700;
  }
  return (
    <Text style={[styles.text, { color }]} accessibilityLiveRegion="polite">
      {text}
    </Text>
  );
}

const styles = StyleSheet.create({
  text: { fontSize: 13 },
});
