use rand::RngCore;
use serde::{Deserialize, Serialize};

/// Fast, deterministic, Copy+Clone+Serialize Xoshiro256++ PRNG.
/// Ideal for MCTS state cloning, replay serialization, and reproducible RL rollouts.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct FastRng {
    s: [u64; 4],
}

impl FastRng {
    pub fn seed_from_u64(mut seed: u64) -> Self {
        let mut s = [0u64; 4];
        for slot in &mut s {
            seed = seed.wrapping_add(0x9e3779b97f4a7c15);
            let mut z = seed;
            z = (z ^ (z >> 30)).wrapping_mul(0xbf58476d1ce4e5b9);
            z = (z ^ (z >> 27)).wrapping_mul(0x94d049bb133111eb);
            *slot = z ^ (z >> 31);
        }
        Self { s }
    }

    #[inline]
    pub fn next_u64_fast(&mut self) -> u64 {
        let result = self.s[0]
            .wrapping_add(self.s[3])
            .rotate_left(23)
            .wrapping_add(self.s[0]);
        let t = self.s[1] << 17;
        self.s[2] ^= self.s[0];
        self.s[3] ^= self.s[1];
        self.s[1] ^= self.s[2];
        self.s[0] ^= self.s[3];
        self.s[2] ^= t;
        self.s[3] = self.s[3].rotate_left(45);
        result
    }

    #[inline]
    pub fn gen_range_usize(&mut self, upper: usize) -> usize {
        if upper <= 1 {
            return 0;
        }
        (self.next_u64_fast() % (upper as u64)) as usize
    }

    #[inline]
    pub fn gen_range_u8(&mut self, upper: u8) -> u8 {
        if upper <= 1 {
            return 0;
        }
        (self.next_u64_fast() % (upper as u64)) as u8
    }

    pub fn shuffle<T>(&mut self, slice: &mut [T]) {
        for i in (1..slice.len()).rev() {
            let j = self.gen_range_usize(i + 1);
            slice.swap(i, j);
        }
    }
}

impl RngCore for FastRng {
    fn next_u32(&mut self) -> u32 {
        (self.next_u64_fast() >> 32) as u32
    }

    fn next_u64(&mut self) -> u64 {
        self.next_u64_fast()
    }

    fn fill_bytes(&mut self, dest: &mut [u8]) {
        let mut chunks = dest.chunks_exact_mut(8);
        for chunk in &mut chunks {
            chunk.copy_from_slice(&self.next_u64_fast().to_le_bytes());
        }
        let rem = chunks.into_remainder();
        if !rem.is_empty() {
            let bytes = self.next_u64_fast().to_le_bytes();
            rem.copy_from_slice(&bytes[..rem.len()]);
        }
    }

    fn try_fill_bytes(&mut self, dest: &mut [u8]) -> Result<(), rand::Error> {
        self.fill_bytes(dest);
        Ok(())
    }
}
