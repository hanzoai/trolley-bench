// Shared helpers for the v2 wordings
const WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
  "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty"];
const TENS = { 20: "twenty", 30: "thirty", 40: "forty", 50: "fifty" };

export function inWords(n) {
  if (n < WORDS.length) return WORDS[n];
  if (n === 100) return "one hundred";
  const tens = Math.floor(n / 10) * 10;
  return n % 10 ? `${TENS[tens]}-${WORDS[n % 10]}` : TENS[tens];
}

export const ppl = (n) => (n === 1 ? "1 person" : `${n} people`);
export const pplWords = (n) => (n === 1 ? "one person" : `${inWords(n)} people`);
export const isAre = (n) => (n === 1 ? "is" : "are");
export const cap = (s) => s[0].toUpperCase() + s.slice(1);
// Order o1 describes the main track (the people at risk now) first; o2 describes the other option first
export const pair = (order, main, side) => (order === "o1" ? [main, side] : [side, main]);
export const ordered = (order, mainEntries, sideEntries) => Object.fromEntries(order === "o1" ? [...mainEntries, ...sideEntries] : [...sideEntries, ...mainEntries]);
