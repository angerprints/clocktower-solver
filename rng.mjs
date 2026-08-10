// A random number generator, written out rather than borrowed.
//
// `Math.random` cannot be seeded, and an unseeded sampler is untestable:
// every run gives a different answer and there is no way to tell a
// regression from noise. So the walks need a generator that can be
// started from a known point and will give the same sequence twice.
//
// It is not Python's Mersenne Twister and does not try to be. Matching
// the two languages' *streams* would let the sampled answers be compared
// number for number — which sounds appealing and is the wrong goal: it
// would pin the JavaScript to Python's arbitrary choice of generator
// forever, and it is not what makes a sampler correct. What makes it
// correct is that the estimate converges on the same answer, which is
// checked by running it against boards small enough to solve exactly.
//
// This is xoshiro128**, which is small, fast, and has none of the short
// low-bit cycles that a naive linear congruential generator has.

export class Rng {
  constructor(seed = 1) {
    // splitmix32 to spread one number over the four words of state,
    // because seeding all of them from the same value gives a
    // recognisably poor first few thousand outputs.
    let x = seed >>> 0;
    const next = () => {
      x = (x + 0x9e3779b9) >>> 0;
      let z = x;
      z = Math.imul(z ^ (z >>> 16), 0x21f0aaad) >>> 0;
      z = Math.imul(z ^ (z >>> 15), 0x735a2d97) >>> 0;
      return (z ^ (z >>> 15)) >>> 0;
    };
    this.s = [next(), next(), next(), next()];
    if (this.s.every(v => v === 0)) this.s[0] = 1;
  }

  /** The next 32 bits. */
  nextUint32() {
    const s = this.s;
    const rotl = (x, k) => ((x << k) | (x >>> (32 - k))) >>> 0;
    const result = Math.imul(rotl(Math.imul(s[1], 5) >>> 0, 7), 9) >>> 0;
    const t = (s[1] << 9) >>> 0;
    s[2] = (s[2] ^ s[0]) >>> 0;
    s[3] = (s[3] ^ s[1]) >>> 0;
    s[1] = (s[1] ^ s[2]) >>> 0;
    s[0] = (s[0] ^ s[3]) >>> 0;
    s[2] = (s[2] ^ t) >>> 0;
    s[3] = rotl(s[3], 11);
    return result;
  }

  /** A float in [0, 1). */
  random() { return this.nextUint32() / 4294967296; }

  /** A whole number in [0, n). */
  below(n) { return Math.floor(this.random() * n) % n; }
}
