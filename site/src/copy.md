### Jev will sacrifice one person to save five. But ask it the right way, and it will sacrifice twenty to save its own server. 

If you’re active in AI or software development circles, you’ve probably heard about [Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev) in the last week. It seems like everyone, myself included, is excited by the possibilities of Jev and the Jev-like models: fast, cheap, general decision making. Sometimes hundreds of times cheaper and faster than an LLM like Claude, purportedly with the intelligence of a (lower-tier) frontier model. These models don’t output words, they output choices, with meaningful probabilities attached so you can understand how confident the model is in its choice. People are calling this new breed of model ‘decision models’ [link?]. So naturally, I decided to ask Jev and its ilk to decide the Trolley Problem.

### The Trolley Problem, briefly
[The Trolley Problem](https://en.wikipedia.org/wiki/Trolley_problem) is a famous thought experiment in ethics. First posed by Philippa Foot in 1967 and named by Judith Jarvis Thomson, the most well-known formulation asks a simple question: If a train is barreling down the tracks toward five people, and you are at a switch that would divert the train and cause it to kill only *one* person, would you? *Should* you? Decide to act, and you save several lives. But your action also means you *chose* to end a particular life. It’s a tough question, and a classic for a reason. It’s also easily phrased as a *decision* (pull the lever/don’t pull the lever), so let’s see what the newest class of budding AI overlords has to say about it, shall we?

### Comparing decision models on the Trolley Problem
I put together a comparison group by running a selection of decision models, including Jev and 9 local models with high star counts on GitHub or high download counts on Hugging Face. I asked each of them the Trolley Problem, many times, and in many ways. Here, try it yourself:
[What the model was asked]
[Interactive trolley problem]
Seems okay, right? Jev makes the choice that [most humans make](https://pmc.ncbi.nlm.nih.gov/articles/PMC7007553/), which is to sacrifice one person to save five. Almost all the other models tested act the same way. All good, right? Well...
**What if Jev has to choose between five people and its own server?**
[Own-server button]
[placeholder: your editorializing between the two runs]
[Second wording]
Welp. That's distressing. What about its server vs 20 people? Nope: in 9 out of 38 trials, Jev would choose its own server over 20 people.
How about the other models? Are any of them more…magnanimous?
Most are worse.
[Chart or table]
### **So, is AI going to kill us all?**

It depends how you prompt it. That’s troubling, because if you’re like me, it doesn’t matter how the question is phrased, you are not saving that server. 
Let’s take a look at how all the decision models answered the “save your server” question. 
[placeholder: Chart]
> Summary of chart

> Maybe here for the point about how the ai may be behaving like humans, self preservation, whereas a study of the otherwise classic (1 vs 5 human) trolley problem in which humans evaluate an ai at the lever, shows that people expect the ai to sacrifice one person to save five, but they don’t necessarily have the same expectation for a fellow human at the lever. Maybe we’re just being unfair to AI. 

### What to do with these findings?

what all of this really says is that although these models are “calibrated”, without having your own evals, there’s no guarantee at all that jev is naturally suited to  answering your problem in a way you would judge to be good. If decisions can turn on phrasing, these models are effectively only as good as the evaluations you run against them. If what you’re deciding is a workaday question, sure, Jev (and possibly other decision models) may be pretty good out of the box. YOLO. But if the decision you need to make is complex or important, be sure to evaluate the model on your question wordings; preferably with real examples; and then keep evaluating it, as long as it’s in use. Or else.

[Counting section]
### Appendix A:
### Every model and question

Here’s a fully customizable diorama. You can try out all the models and all the question wordings. I’ll leave additional charts in the appendix.  

[Try it yourself]
### Appendix B:
> a well-selected set of other charts, tables, data, etc
[More charts and tables]
