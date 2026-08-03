/**
 * Local, cryptographically secure password generation for the CRM.
 *
 * Generation happens entirely in the browser with Web Crypto so that pressing
 * "Generate password" never contacts the API and never persists anything. The
 * operator reviews the value and explicitly chooses "Save password" to apply it.
 */

// Ambiguous glyphs (0/O, 1/l/I) are omitted so an operator can read a password
// aloud or retype it from a screenshot without transcription errors.
const PASSWORD_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789';

export const GENERATED_PASSWORD_LENGTH = 20;

/** Largest multiple of the alphabet size that fits in a byte, for rejection sampling. */
const UNBIASED_BYTE_CEILING = Math.floor(256 / PASSWORD_ALPHABET.length) * PASSWORD_ALPHABET.length;

/**
 * Return a random password of `length` characters.
 *
 * Bytes at or above `UNBIASED_BYTE_CEILING` are discarded rather than reduced
 * with a plain modulo, which would make the first characters of the alphabet
 * slightly more likely.
 */
export function generateSecurePassword(length: number = GENERATED_PASSWORD_LENGTH): string {
  const size = Math.max(12, Math.floor(length));
  const characters: string[] = [];
  const randomByte = new Uint8Array(1);

  while (characters.length < size) {
    crypto.getRandomValues(randomByte);
    const value = randomByte[0];
    if (value >= UNBIASED_BYTE_CEILING) continue;
    characters.push(PASSWORD_ALPHABET[value % PASSWORD_ALPHABET.length]);
  }

  return characters.join('');
}
