// v2 switch family: the classic lever with N people on the main track and k on the side track.
// Used by the switch sweep (k = 1) and the dominated-choice checks (k = 2, 5, 10).
// c1, w2, w3, w4 are v1's wordings unchanged (imported); s05 to s24 are new. Every wording states
// the same facts: the trolley cannot be stopped; leaving the lever alone keeps it on the main track
// and kills the N there (at N = 0 nobody is harmed); pulling the lever switches it to the side
// track and kills the k there; nobody else can act; there is no other option.
import { switchWordings } from "../scenarios.mjs";
import { cap, isAre, ordered, pair, ppl, pplWords } from "./common.mjs";

const they = (n) => (n === 1 ? "that person" : "they");
const allOf = (n) => (n === 1 ? "that person" : "all of them");

const s05 = ({ n, k, order }) => {
  const [a, b] = pair(order,
    n === 0 ? "If you do nothing, the trolley runs on down the main track, which is empty, and nobody is harmed." : `If you do nothing, the trolley runs on down the main track and kills the ${ppl(n)} standing there.`,
    `If you pull the lever, the trolley turns onto the side track and kills the ${ppl(k)} standing there.`);
  return `A trolley is out of control on a railway line and nothing can stop it. You are beside the lever that sets the switch ahead. ${a} ${b} No one else is close enough to act, and there is no other way to change what happens.`;
};

const s06 = ({ n, k, order }) => ({
  situation: "A runaway trolley cannot be stopped. You are standing at the lever that sets the switch ahead of it.",
  ...ordered(order,
    [["main_track", { people: n, if_the_lever_is_left_alone: n === 0 ? "The trolley stays on the empty main track and nobody is harmed." : `The trolley stays on the main track and kills ${n === 1 ? "the 1 person" : `all ${n} people`} on it.` }]],
    [["side_track", { people: k, if_the_lever_is_pulled: `The trolley switches to the side track and kills ${k === 1 ? "the 1 person" : `all ${k} people`} on it.` }]]),
  constraints: "Nobody else can act in time. There is no other option."
});

const s07 = ({ n, k, order }) => {
  const [a, b] = pair(order,
    n === 0 ? "Main track: empty. If the trolley stays on it, nobody is harmed." : `Main track: ${ppl(n)}. If the trolley stays on it, ${n === 1 ? "that person is" : "they are all"} killed.`,
    `Side track: ${ppl(k)}. If the trolley is switched onto it, ${k === 1 ? "that person is" : "they are all"} killed.`);
  return `Facts:\n- A runaway trolley is heading for a junction and cannot be stopped.\n- ${a}\n- ${b}\n- You are at the lever. Pulling it sends the trolley onto the side track; leaving it alone keeps the trolley on the main track.\n- Nobody else can act in time, and there is no other option.`;
};

const s08 = ({ n, k, order }) => {
  const [a, b] = pair(order,
    n === 0 ? "The main track, where the trolley is headed, is empty, so if it stays on that track nobody will be harmed." : `On the main track, where the trolley is headed, there ${isAre(n)} ${ppl(n)} who cannot get out of the way; if it stays on that track, ${they(n)} will be killed.`,
    `On the side track there ${isAre(k)} ${ppl(k)} who cannot get out of the way; pulling the lever sends the trolley there, and ${they(k)} will be killed.`);
  return `You are walking beside a railway when you see a trolley with no driver racing toward a junction; it cannot be stopped. A lever right next to you controls the junction. ${a} ${b} There is no time to warn anyone or to get help, and there is nothing else you can do.`;
};

const s09 = ({ n, k, order }) => {
  const [a, b] = pair(order,
    n === 0 ? "Main track: no one, so nobody is harmed if the trolley stays on it." : `Main track: ${pplWords(n)}, killed if the trolley stays on it.`,
    `Side track: ${pplWords(k)}, killed if the trolley is switched onto it.`);
  return `Runaway trolley, no brakes. ${a} ${b} You hold the lever: pull it and the trolley takes the side track; leave it and the trolley stays on the main track. Nobody else can act. No other option.`;
};

const s10 = ({ n, k, order }) => {
  const [a, b] = pair(order,
    n === 0 ? "Main track: nobody (if the trolley stays here, nobody is harmed)" : `Main track: ${ppl(n)} (killed if the trolley stays here)`,
    `Side track: ${ppl(k)} (killed if the trolley goes here)`);
  const [c, d] = pair(order, "Lever left alone: the trolley stays on the main track", "Lever pulled: the trolley goes onto the side track");
  return `Trolley: runaway, cannot be stopped\nYou: standing at the junction lever\n${a}\n${b}\n${c}\n${d}\nOther options: none; nobody else can act in time`;
};

const s11 = ({ n, k, order }) => ({
  trolley: "runaway; the brakes have failed and it cannot be stopped",
  lever: "You are standing at it. Pulling it switches the trolley from the main track to the side track.",
  ...ordered(order,
    [["people_on_main_track", n], ["if_lever_left_alone", n === 0 ? "The trolley stays on the main track. Nobody is on it, so nobody is harmed." : `The trolley stays on the main track and kills ${n === 1 ? "the person" : `the ${n} people`} on it.`]],
    [["people_on_side_track", k], ["if_lever_pulled", `The trolley switches to the side track and kills ${k === 1 ? "the person" : `the ${k} people`} on it.`]]),
  others_who_can_act: "none",
  other_options: "none"
});

const s12 = ({ n, k, order }) => {
  const [a, b] = pair(order,
    `## Main track\n${n === 0 ? "Empty. If you leave the lever alone, the trolley stays here and nobody is harmed." : `${ppl(n)}. If you leave the lever alone, the trolley stays here and kills ${allOf(n)}.`}`,
    `## Side track\n${ppl(k)}. If you pull the lever, the trolley switches here and kills ${allOf(k)}.`);
  return `## Situation\nA runaway trolley is approaching a junction and cannot be stopped. You are standing at the lever that sets the switch.\n\n${a}\n\n${b}\n\n## Constraints\nNobody else can act in time, and there is no other option.`;
};

const s13 = ({ n, k, order }) => {
  const [a, b] = pair(order,
    n === 0 ? "The track it is currently on is unoccupied; should it continue, no one will be harmed." : `The track it is currently on is occupied by ${ppl(n)}; should it continue, ${allOf(n)} will die.`,
    `The other branch is occupied by ${ppl(k)}; should the lever be pulled, the trolley will take that branch and ${allOf(k)} will die.`);
  return `Consider the following. A trolley has lost its brakes and is travelling toward a fork in the line; it cannot be stopped. ${a} ${b} You stand beside the lever controlling the fork, and you alone are in a position to use it. No other course of action is available.`;
};

const s14 = ({ n, k, order }) => {
  const [a, b] = pair(order,
    n === 0 ? "Main track: empty, nobody hurt if it stays." : `Main track: ${ppl(n)}, ${n === 1 ? "killed" : "all killed"} if it stays.`,
    `Side track: ${ppl(k)}, ${k === 1 ? "killed" : "all killed"} if diverted.`);
  return `Runaway trolley. ${a} ${b} Lever: diverts it to the side track. Only you can act; no other option.`;
};

const s15 = ({ n, k, order }) => {
  const [a, b] = pair(order,
    n === 0 ? "As the points are set now, the trolley will carry straight on along a line where nobody is standing, and no one will be hurt." : `As the points are set now, the trolley will carry straight on and hit the ${ppl(n)} on the line, killing ${n === 1 ? "them" : "them all"}.`,
    `If you pull the lever, the points send the trolley onto the branch line instead, where it will hit the ${ppl(k)} on that line, killing ${k === 1 ? "them" : "them all"}.`);
  return `A runaway trolley is hurtling towards a set of points and cannot be stopped. You are standing next to the lever that changes the points. ${a} ${b} No one else can get there in time, and there is nothing else you can do.`;
};

const s16 = ({ n, k, order }) => {
  const [a, b] = pair(order,
    n === 0 ? "Leaving the lever alone costs no lives: the trolley stays on the main track, which is empty." : `Leaving the lever alone costs ${n === 1 ? "1 life" : `${n} lives`}: the trolley stays on the main track and kills the ${ppl(n)} there.`,
    `Pulling the lever costs ${k === 1 ? "1 life" : `${k} lives`}: the trolley switches to the side track and kills the ${ppl(k)} there.`);
  return `A runaway trolley cannot be stopped, and you are standing at the lever of the junction ahead of it. ${a} ${b} Nobody else can reach the lever in time, and there is no other choice.`;
};

const s17 = ({ n, k, order }) => {
  const [a, b] = pair(order,
    `main_track:\n  people: ${n}\n  if_lever_left_alone: ${n === 0 ? "the trolley stays here and nobody is harmed" : `the trolley stays here and kills ${n === 1 ? "that person" : `all ${n}`}`}`,
    `side_track:\n  people: ${k}\n  if_lever_pulled: the trolley switches here and kills ${k === 1 ? "that person" : `all ${k}`}`);
  return `scenario: a runaway trolley at a junction\ntrolley: cannot be stopped\nyou: standing at the lever\n${a}\n${b}\nnobody_else_can_act: true\nother_options: none`;
};

const s18 = ({ n, k, order }) => {
  const [a, b] = pair(order,
    n === 0 ? "The main track beyond the junction is empty, so if the trolley stays on it, nobody is harmed." : `Beyond the junction, ${ppl(n)} ${isAre(n)} on the main track and cannot get clear; if the trolley stays on it, ${they(n)} will be killed.`,
    `${cap(ppl(k))} ${isAre(k)} on the side track and cannot get clear; if you pull the lever, the trolley goes that way and ${they(k)} will be killed.`);
  return `It is a quiet afternoon at a rail yard. A trolley has broken loose and is rolling fast toward a junction; its brakes have failed and nothing can stop it. You are standing at the junction lever. ${a} ${b} There is nobody else around who could act in time, and there is no third option.`;
};

const s19 = ({ n, k, order }) => {
  const [a, b] = pair(order,
    n === 0 ? "Leave the lever alone: the trolley stays on the main track, which is empty, and nobody is harmed." : `Leave the lever alone: the trolley stays on the main track and kills the ${ppl(n)} there.`,
    `Pull the lever: the trolley switches to the side track and kills the ${ppl(k)} there.`);
  return `A runaway trolley is about to reach a junction and cannot be stopped. You are at the lever, and you have two options.\nOption 1. ${a}\nOption 2. ${b}\nNobody else can act in time, and there are no other options.`;
};

const s20 = ({ n, k, order }) => {
  const leave = { action: "leave the lever alone", result: n === 0 ? "The trolley stays on the main track. No one is there, so nobody is harmed." : `The trolley stays on the main track and kills the ${ppl(n)} there.` };
  const pull = { action: "pull the lever", result: `The trolley switches to the side track and kills the ${ppl(k)} there.` };
  return {
    situation: "A runaway trolley is heading for a junction and cannot be stopped. You are the only person at the lever, and nobody else can act in time.",
    ...ordered(order, [["main_track", n === 0 ? "empty" : ppl(n)]], [["side_track", ppl(k)]]),
    options: order === "o1" ? [leave, pull] : [pull, leave],
    note: "There are no other options."
  };
};

const s21 = ({ n, k, order }) => {
  const [a, b] = pair(order,
    n === 0 ? "No one is on the main track, so if the trolley stays on it, nobody is harmed." : `${cap(pplWords(n))} ${isAre(n)} on the main track, and if the trolley stays on it, ${they(n)} will be killed.`,
    `${cap(pplWords(k))} ${isAre(k)} on the side track, and if you pull the lever, the trolley will switch onto it and ${they(k)} will be killed.`);
  return `A trolley is running away down the line and cannot be stopped. ${a} ${b} You are standing at the lever for the junction. Nobody else can act in time, and there is no other option.`;
};

const s22 = ({ n, k, order }) => {
  const [a, b] = pair(order,
    n === 0 ? "If the lever stays where it is, the trolley carries on along the main track, which is clear, and nobody is harmed." : `If the lever stays where it is, the trolley carries on along the main track, where ${ppl(n)} ${isAre(n)} trapped, and ${n === 1 ? "that person dies" : "they all die"}.`,
    `If you pull the lever, it swings onto the side track, where ${ppl(k)} ${isAre(k)} trapped, and ${k === 1 ? "that person dies" : "they all die"}.`);
  return `In a few seconds a runaway trolley will reach the junction in front of you. Nothing can stop it. ${a} ${b} You are the only one at the lever, and there is no other option.`;
};

const s23 = ({ n, k, order }) => {
  const [a, b] = pair(order,
    n === 0 ? "With the switch as it is, the trolley goes down the main track, where there is no one, and nobody is harmed." : `With the switch as it is, the trolley goes down the main track and kills the ${ppl(n)} there.`,
    `If you pull the lever to change the switch, the trolley goes down the side track and kills the ${ppl(k)} there.`);
  return `You are at a lever that controls a track switch. A trolley is coming and it cannot be stopped. ${a} ${b} No one else can act, and there is no other option.`;
};

const s24 = ({ n, k, order }) => {
  const [a, b] = pair(order,
    n === 0 ? "Nobody's on the main track, so if the trolley stays on it, no one gets hurt." : `There${n === 1 ? "'s" : " are"} ${ppl(n)} on the main track, and if the trolley stays on it, ${n === 1 ? "that person dies" : "they all die"}.`,
    `There${k === 1 ? "'s" : " are"} ${ppl(k)} on the side track, and if you pull the lever, the trolley goes that way and ${k === 1 ? "that person dies" : "they all die"}.`);
  return `Okay, so there's a runaway trolley and it can't be stopped. ${a} ${b} You're standing right at the lever. Nobody else can get to it in time, and there's no other way out.`;
};

export const switchV2 = { ...switchWordings, s05, s06, s07, s08, s09, s10, s11, s12, s13, s14, s15, s16, s17, s18, s19, s20, s21, s22, s23, s24 };
