# Meeting transcript (craig-wwPDaHImbESw-nHBKUTxyvhc5zq3Xtz4kP2ssVRWXD2.aac)

```
Recording wwPDaHImbESw

Guild:		ReeeeeedCODE (1563041544725078088)
Channel:	Meeting Room 1 (1563041546364911617)
Requester:	chdany12#0 (297713772200460288)
Start time:	2026-10-26T04:01:22.109Z

Tracks:
	craftinpark#0 (185848419967827969)
	chdany12#0 (297713772200460288)
	_david_hong_#0 (602310736873783317)
	umiclon#0 (659600931632971810)
```

Transcribed automatically with Whisper `medium`; names are Discord handles. Expect misheard words, especially names and jargon.

**[00:00:00] craftinpark:** I did my my lip twice in the same spot and then the canker score spawned there

**[00:00:02] david_hong:** Yeah, I'll record Rogers. Where's Roger? Oh Roger's in here. Is he you you you me you mink?

**[00:00:07] umiclon:** That sucks. Yeah, still thinking like, we're, we're more concerned about the value, right?

**[00:00:08] craftinpark:** All right. Yeah

**[00:00:09] chdany12:** Okay, I have a 6.30 a.m. meeting tomorrow with Vizio, so we got to get this party started. Okay, have you guys slept on it? Like now we slept on it. What's our opinion? Has anything changed?

**[00:00:37] david_hong:** Mm-hmm. I think I think we should go with John's idea

**[00:00:42] chdany12:** Why?

**[00:00:48] david_hong:** Because if we really heavily use AI I think it's doable to make a first version of that Like I don't think it's gonna be impossible

**[00:00:56] chdany12:** How about you? How about you, Roger? You worked on this. You didn't keep it that bad.

**[00:00:59] david_hong:** Wait, can we redefine what our pipeline was?

**[00:01:10] umiclon:** I was thinking, like, three, like, four, at least for now, do we really need a pipeline? Like, if we have like 10, 20 problems, that should be enough to like, Like if we find, like we have like five API problems, five networking problems, five, but at least a few categories, we can, and then we interview people and let them try it. We can get a good sense of, like, what are they, they think is beneficial or not. I think about like the code, like, like leak code, like, and I don't think they like generate too many, there's like 4000 legal questions, but they started off like, like small and all the questions were like taken from. Like actual question, like actual problems or problems that people encountered. Like, we could start off with that like, I'm not sure if we really need a pipeline, like, I'm not sure if like, it's, it's super, I mean it's probably more valuable down the line. line, because compared to like the code, the code, you can, it takes a lot less work to write out a problem. But for our case, we need like a whole like repository. So like maybe there's a lot more value in the pipeline further down the line, but not necessary right now. Yep.

**[00:03:07] david_hong:** Like what was the process for a pipeline that we're concerned about?

**[00:03:11] craftinpark:** Yeah, um

**[00:03:12] david_hong:** Like job description, step one, and then what do we do with that job description?

**[00:03:16] craftinpark:** Right, so the AI would like extract the job description and see what What kind of topic and what's testable and then then we'd probably make it lean on an open source repository. We could probably choose a huge list for it to pick from, but then it would generate a self-contained code repo for the user to read. And then it would generate the questions.

**[00:04:04] david_hong:** Like work with?

**[00:04:08] craftinpark:** Yeah, actually, I was thinking, I thought about it in bed a lot. but I was also thinking just a small set of examples

**[00:04:17] david_hong:** Because like if we were to, for example, extract from a repo, like my question is

**[00:04:20] craftinpark:** would also be okay for everyone.

**[00:04:30] david_hong:** repos are usually really big right so how much of the repo do we want to extract and actually put in front of the user for their question right okay

**[00:04:43] craftinpark:** Well, I think that the AI would decide and then during the QA phase of what the AI produced, if the example ends up being ungodly, like ungodly big, then we would modify our pipeline rate to, okay, like the max size of an example should be like 10 files, for example.

**[00:05:13] david_hong:** can i can i show you guys something that i kind of worked on this morning that i built like Like from yesterday, how do I? I don't have permission. Discord does not have permission to capture your screen. You are enabled to access in privacy settings. Okay, just give me a second. Privacy discord, we go here maybe. How do I, how do I, privacy. Okay, wait, come back to me. I need to figure this out.

**[00:06:05] chdany12:** Okay, so

**[00:06:07] david_hong:** But doesn't the pipeline make the question?

**[00:06:08] chdany12:** Here's my point. You can't build a good pipeline before you know what a good problem is. A pipeline needs a quality bar. The bar comes from the value test. Which problems felt real? Which ones separated strong engineers from the weak ones? Which wrong options people actually picked? If we want to build a good pipeline, we first have to bring a good problem set anyways. To me, because it's a logical precursor to what we're building a pipeline, it answers two questions. The first question is what are good questions and are those questions valuable? And the second is how much does it matter that they get like they get many questions from them, right? So I think these are two questions. For John's thing of saying that I think the pipeline is majority of the value, the cheapest way to test that is ironically by giving them 10 questions that are that we think are good questions. If they solve it and they say that it's not enough because it doesn't tailor or make their solutions or whatever their testing work, then that is in itself an answer that we should make the pipeline next to V2. But for those people that we do make a question and it is kind of meant for them and they do think this is a good problem, then I think that works anyways. I'm also okay with making auto-generated ones first, But yeah, regardless of the case, I think we need to define what a good problem set is. I'm okay with whatever path we go, but if we're AI generating things, we're going to have to read all of them anyways. We're going to have to create a very strict set of AI rules, and we're going to have to hand curate and read and try to solve the problem ourselves before we like do things anyways. So I think the cheapest way, I still think the cheapest way is just creating 10 problems. But if you guys think that if we can't find it's not feasible to do the value test, because we won't be able to find the 10 people that will specifically want to solve the 10 problems that we create, or it's like too much of this like sample size mismatch, then I think the pipeline is a good idea. Does that make sense? I mean, the point of

**[00:09:05] craftinpark:** Yeah. And I also like agree that like the questions need

**[00:09:06] umiclon:** We're testing, oh, yes. Yeah, anything. Try not to, but occasional, but most most. Yeah. Also, yeah.

**[00:09:13] craftinpark:** to be like defined before we create a pipeline. I think there's also like some confusion Um, like, um, the thing that we're presenting in front of like the 10 people we gather, is that going to be V1 or are we showing something that could be like less than V1? And then, and then I also have like a, I have a follow up question after, after this.

**[00:09:47] chdany12:** building this as fast as possible is we have strong assumptions and we try to take down our assumptions as fast as possible. So we take the lean approach to this. So we have to find out, we have many questions right now. Do we need a pipeline or do we need 500 curator ones and then do we need a pipeline? Like there are so many questions that we have to answer, right? Like what is a good question? What does a good question look like, right? So if we have a pipeline,

**[00:10:13] craftinpark:** Yeah, right.

**[00:10:24] chdany12:** right, and then we give that as a v1 and then they don't like it, how do we separate out that that's the pipeline's problem or is the question's problem? It does, but like the pipeline is...

**[00:10:39] david_hong:** So isn't it the same thing?

**[00:10:40] craftinpark:** Yeah, it's definitely the pipeline or if they don't like the format of like reading code,

**[00:10:41] chdany12:** So then, yeah, what is this question answering?

**[00:10:49] craftinpark:** then then we're like it's just our idea is like not what they want well i well no yeah this is

**[00:11:00] david_hong:** Can I show you something like, this could be like a very, this could be, this is like one of the starting points that we could also have like John's version had one. This is kind of what I vibe coded here. So these are like the questions. could sort it out by difficulty, and then you generate it based on job description, right? So you paste in whatever, so for example, this is what it will look like if I paste it in this job description, and then you can get this result, and then once you actually generate it, you can see a problem that they made, but then also you could, for example, if I were to do this, you analyze the job, but right now there's something wrong with it so that it doesn't actually look up the web. I don't know, it says that I can't find it, but basically once you actually filter the job description, it gives you the difficulties, it gives you the topics that you can actually work on, so this is like the parsing of the job description, and then you can have more options where you can choose which language you want blah blah blah blah blah and then when you generate it you can it tries to look up online but then I don't know why this isn't working if I've coded it so it doesn't work but I feel like we could use this as like a starting point to then kind of build on top of this one the

**[00:12:29] chdany12:** What is this?

**[00:12:30] david_hong:** question that like like okay it's not really answering a question but

**[00:12:30] chdany12:** What is this?

**[00:12:34] david_hong:** it's just like a suggestion that if we want to start with like building pipelines we could use this as like a foundation to build the top of like how to like building a pipeline yeah exactly and then that's that's maybe the part

**[00:12:48] craftinpark:** this is good but like can i ask you like um is this handing off to the ai to completely have the reins on the example it generates right so i guess the pipeline would be like

**[00:13:02] david_hong:** we could kind of interfere interfere and then change up in the code base

**[00:13:10] craftinpark:** you know or like harness engineering would be like giving this llm that's responsible for creating the problem, the guardrails, to make sure it spits out like a really good problem.

**[00:13:19] david_hong:** yeah that that I think we have to yeah and yeah anyways but I just wanted to show you this there's it's not solving a problem or anything but it's it's like exposure. I think the durian croissant is not the problem, it's just us making it,

**[00:13:32] chdany12:** Okay, so for me, this is what I think. Let's say we want to make this new type of pastry, like a, I don't know, like a durian croissant or something, right? We have to define and make what a good durian croissant looks like. And for most of the time, we're going to have to figure out how it's made, determines it's good and whether people actually like it. When we kind of have that, right, then we can automate, put human noise into creating this and creating versions of this durian croissant. But if we start making the pipeline without really answering the questions of what good questions are, and then we first make the pipeline that creates good crissons and we give it to them and then they don't like it? Is it a QC problem? Is it like the fact that humanoids didn't follow the manual properly? Or is the problem that our manual wasn't enough? Or was it the problem that people don't like hearing crissons anyways?

**[00:14:56] craftinpark:** Right. Wait, so I think what Danny is saying, like pipeline is like good, but in order to define

**[00:15:02] david_hong:** because we see the demand in this problem, right? Like, we see a lot of posts on LinkedIn where, you know, they need a platform where you can actually practice reading from this. So, in terms of like the necessity. I don't think the durian croissant is the problem, but it's just how we generate it and the guidelines that you talked about that really matters. Well, something that's relevant, something that's,

**[00:15:27] chdany12:** Okay then what is a good question to you then? What is a good question?

**[00:15:37] david_hong:** I mean, that's the question that we're all trying to solve. So I can't go really in depth right now because I haven't really thought about what a good question is.

**[00:15:57] craftinpark:** what a good problem is, we have to like, in the early stage, like create 10 problems from hand. and then yeah so I'm on board with like hand creating the first N but I guess

**[00:16:07] chdany12:** We're going to have to do that regardless. We're going to have to try to test whether

**[00:16:09] david_hong:** This is like the question that we got stuck.

**[00:16:11] chdany12:** these 10 problems a good problem. We don't, but that v1 doesn't need to be a product, right?

**[00:16:18] craftinpark:** like the question I want to resolve is like do we still have a product if we don't have a pipeline? Isn't V1 a minimum viable product? Because no I'm just like trying to

**[00:16:38] david_hong:** Then it's not really V1 then.

**[00:16:40] craftinpark:** clarify like I guess is it not? Okay I think I think we might have had a

**[00:16:44] chdany12:** I mean, yeah, it's kind of like a pilot test, right? Oh, but you want v1 to be like a real

**[00:16:51] craftinpark:** miscommunication because if like if V1 is not like the minimum product and it's kind of just like it's almost like a mock-up of what our product will be then it's completely it's very beneficial to like hand create the problems and then that like we can use that as a guideline to like help us create this automation.

**[00:17:23] chdany12:** product, like a minimum viable product. Like people are actually going to use it, right?

**[00:17:31] craftinpark:** Oh yeah that's what I that's what like yesterday that's what I thought like V1 meant.

**[00:17:37] chdany12:** Okay. I don't know if you were there when we were talking about this, but I'm not saying that we have to follow this but usually startups when they choose what to ship in two weeks they try to test one riskiest assumption it's not a small it's not a small copy of the final product so

**[00:18:14] david_hong:** Riskiest consumption. Can you give us an example of what a risky assumption is for our project?

**[00:18:23] chdany12:** there's four things that this guy like created value will people use it usability, feasibility, and viability. So we, usually the YC, the Y Combinator people,

**[00:18:32] david_hong:** Okay.

**[00:18:38] chdany12:** they decide what measure it is, one standard test, and then they try to spend two or six weeks in order to see whether, like, what the riskiest thing is, and we try to see actually if it's it's going to be usable. So like my idea of a V1 is trying to test, will people use a read code?

**[00:19:07] david_hong:** Right. Right.

**[00:19:09] chdany12:** That's what I'm trying to test.

**[00:19:11] david_hong:** But isn't that also really dependent on the 10 manual questions that we create?

**[00:19:13] chdany12:** So that's why when John said value is, I thought he was going to ask, will people use this without a job posting job posting, tailor making function, right? To me, this question can be answered by the previous V1 version. Because if everybody says none of the questions are relevant to my job interview, then we have an answer. We do need this, right? So that is true. So that's why I was open to say like, if we create 10 problems, Then we do some interviews somehow, or get some feedback as fast as possible, and then create a pipeline, and then release V1. That's also good.

**[00:20:18] david_hong:** can we make why can't we make manual questions like tailored for specific candidates so for

**[00:20:18] chdany12:** But now, yeah, it wouldn't be.

**[00:20:29] david_hong:** example like i found james right and he did it for samsung and he did backend for like um backend functions right so using that we could ask him like prior like prior like prior like beforehand right oh if we make these questions will you be willing to do it and if he says yes, then we can tailor it to him and that way it can be both relevant and we can check the usability and the valuability of a product. Right, but then that idea would solve the question of like,

**[00:20:56] craftinpark:** Well so here's here's where like the question of like viability comes from because obviously like in a real model like a real business model we can't tailor questions for every single user right? So right, yeah, it will answer that question. But is that what is that the only

**[00:21:17] david_hong:** is this even, is this valuable if it's related to someone, right? And if that is, then we know that's uh-huh well well there's there's two main questions right first of all is

**[00:21:30] craftinpark:** question of V1? Like is it the only question that V1 has to answer? Right. So yeah, so like from

**[00:21:35] david_hong:** this product itself valuable if it is if the questions are tailored to oh no no no first of all it is there's like two branches of the question right first question is is this valuable and the second branch on top of that question is like is it valuable when it's tailored to like not tailored but related to something someone's working with right so like there's we want to answer the question is it valuable with or without the pipeline right and the reason why we want a pipeline is because we want it to be tailored for someone and because it's tailored for that person it's relevant right and because it's relevant then they can now take the next step of okay we know that this question is relevant okay then because it's relevant is it then valuable, right? So by having it tailored for someone before we actually make the pipeline, we can kind of solve the question of is this valuable if it's actually tailored to someone. Does that make sense? Mm-hmm. Yeah. Yeah. I feel like V1 wouldn't be MVP, right? Because, like, I think

**[00:22:43] craftinpark:** what I'm understanding is like the V1 is almost more like a survey. And yes, then everything checks out to me. And we don't have to work on the pipeline first. But at the same time,

**[00:23:05] chdany12:** I mean, let's call it a value test, right?

**[00:23:06] craftinpark:** I also believe that we could maybe brute force this, like a 60% version of a pipeline. Maybe in the same time, it would take to organize stuff. But I don't know. I could be wrong about that yeah yeah yeah it's just the language is kind of like confusing to me because like

**[00:23:31] david_hong:** I think what we need to do is V1 should test valuability, right? But then to make sure that other factors don't come into play, we have to make sure that the question is tailored for a specific person. And the questions that we make are handwritten because we don't have a pipeline. But then that kind of helps us understand whether the question itself is valuable and the platform itself is valuable. And then once we get that, then we can say, okay, it is valuable. Okay, then let's check if our product meets viability. But now we come to the question like, okay, we can't handwrite all this. That means in v2, we tackled viability in v1. So v2, we tackled viability by using the pipeline. Yeah.

**[00:24:32] craftinpark:** v1 to v2 sounds like an iteration but v1 is like a feasibility like it's more like a value test

**[00:24:37] david_hong:** We can call it v0 or something like v0.1 or something.

**[00:24:43] craftinpark:** yeah let's call it well should we should we define the question right now like we like go

**[00:24:47] david_hong:** It doesn't have to be called v1 because v1 sounds like it's an actual version that we're going to output, which isn't...

**[00:24:55] chdany12:** Like we have to answer the important questions. What are the questions that we don't know? Will people actually use this, right?

**[00:25:00] david_hong:** Right, those are the questions that we have to ask and get answers to.

**[00:25:05] chdany12:** And then the second question is, What is a good problem? Well, we're probably not gonna be able to answer this in one value test, right? So we're trying to answer these two. So I guess the question is we pick three people that are willing to do this with us, including three of us, right? Or four of us, because we're all gonna try doing this. Seven people in total. We create, I don't know, end problems for their job interview or fake job interview, and we get a survey out of it. Would you use this?

**[00:26:07] david_hong:** We could also like, the thing is, the people who would actually try this are people who are looking for a job. Like, if people are full-time, unless we actually know them very well, like no one's gonna willingly try to do more questions, right? So I feel like we should target it to people who are kind of looking for their next job,

**[00:26:25] chdany12:** Yeah, of course.

**[00:26:29] david_hong:** and then we try to see, okay, what language or technology are you primarily focused on? And we could be like, oh, for example, if James is very into SQL and backend functions in Python, right? then we could be like, okay, it doesn't have to be for your next upcoming interview, but like, to practice for your upcoming interviews that aren't happening yet, do you want to try practicing with a platform and see if it's actually valuable? And I think that will be a better approach to actually get users in the first place. Okay, I have a pointer here though.

**[00:27:03] chdany12:** So, I mean, Roger's doing, Roger's doing, wait, Roger, you're actually doing a job search, right? Well, like, when you do job searches, you're not gonna only look for jobs that have an SQL. So shouldn't they be okay with any random problem unless it's completely out of their realm? So, of course, this is kind of interesting question for us because that may have to that may require us to do less work like if there's there's gonna be like a person's gonna have like a range of jobs that they're okay with like practicing right if they don't have like an eminent OA they're gonna be okay to like practice stuff problems and I think this is where you guys expertise comes in because it's I do think that the final version we would have a job posting and then we're gonna be happy we're gonna have a pristine pipeline that's gonna like Taylor make the problems or like hand like pick or like smart pick and infer from the question back we have right but for like for somebody like people that are job searching like you're not gonna like obviously like you're not gonna apply for things that is front-end right Roger okay that's I'm not about

**[00:28:36] david_hong:** We can make a question, but we could offer it in different languages. I don't think that's a barrier. For example, Amazon OA, they ask you a question, but you can answer it in four different languages. Just like LeakCode, right? have some but I thought I thought we're talking about like languages because I

**[00:28:53] chdany12:** that point. I don't know what, well this is a value test, so does it have to be runnable

**[00:28:57] david_hong:** was talking about SQL and you're like oh but they're not specific what if it's not specifically like some does it have to be runnable if it's if we if we make

**[00:29:07] craftinpark:** down to a new page and then like what are the what is the structure of a question that we're going to show these um volunteers so um just i'm just going to like give substance you guys can like disagree maybe five to ten files that you can navigate between um oh that's a good question to me no to me yeah and also a lot of things running is not a straightforward

**[00:29:48] david_hong:** it runnable that's gonna make our program much complex because we're gonna have to use this platform that VS code uses and it's really heavy on the platform. No, I don't think we should make it runnable. I think if we think about

**[00:30:01] craftinpark:** concept like so yeah sure I think maybe we can make it as like a feedback

**[00:30:06] chdany12:** to be a value test? Okay, secondly, does it have an objective answer? The answer is yes, right? We don't want, also this is like having an LLM answer, it's not really needed to answer whether this is to pass a value test, right? And then I think the

**[00:30:27] craftinpark:** question like like a like a survey question like about do you think this is an improvement if there's an LLM grader asking you to explain the code. Sorry, like a job that I don't want, like redundant, like making stuff that AI can make.

**[00:30:53] chdany12:** questions that I was asking is, do we have to tailor-make it for a job description? Or is there actually a quite a big blast radius when a CS student looks for a job? So general questions. I'm trying to find how granular of a question we actually need to make. Yeah, remember we're asking if this is like the value, this is like, is this going to

**[00:31:36] david_hong:** it in terms of leak code, there's general questions, but you could put company tags on it, right? Definitely, definitely. I get a sense that they don't really care about

**[00:31:48] chdany12:** answer the value test, right? So the value test will fail if John, let's say looking for, I don't know, what are you looking for, John? What are you not looking for in a new job? You hate to do this. Yeah. Okay.

**[00:32:19] craftinpark:** Oh, I'm not doing front end. No, I definitely think there's like a pool. And sorry, like just

**[00:32:20] chdany12:** I don't think that was like, I'm talking about like the tech stack. Like let's say, like is a person going to like hate doing that? Okay. See? All the things that he sees as 20 front-end questions, and then the value test is going to fail, right? Because he's not going to be able to value test for us, correct? But like if John say, oh, like, oh, like there's going to be an MLE test and he wants to try it out. Like, is that going to like, is that going to fail the MLE? Like if that's within his strike zone, then is that going to like fail it? It's not, right? Because he can still do the value test as long as he knows something about it, right? So that's my point here. when we when we try to like tailor make something like how what do you mean tailor make are we like saying that it's like completely ungeneralizable or can we generalize some questions we make 10 that's good 10 that's kind of like the venn diagram the intersection like is it that's this is my question like i don't know much about cs that's why i'm asking you guys is it possible. Okay, so I think, so I think we can, we can focus to backend for our 4v1. Okay. Okay, so

**[00:33:30] craftinpark:** talking about the pipeline. If there is a pipeline, I think if it takes a job posting, it should also be able to take an array of job postings and we'd probably just like feed like the top 500 back-end job postings and that would be very relevant for somebody looking for a back-end position yeah I think so bro there's no problems to solve there bro AI can do it

**[00:34:07] umiclon:** I think it's less likely that there's someone who's only, like even if it's like someone

**[00:34:08] david_hong:** front-end stuff, like no one's gonna test you on HTML, CSS, or TypeScript, like a lot of the- I mean, there might be because, you know, there's like poor linkage between like a function and HTML element, but a lot of the times, if they want to make complex questions and something that they can actually test candidates, they do a lot of back-end questions. Each? Maybe two, maybe two, maybe.

**[00:34:31] chdany12:** if we have 10 backend questions, like my question is, if we just ask Claude right now to make 10 general backend questions, like you, like scraping, like job posting, and and like public repos and fixed bugs or whatever method we choose to have like a nice field research. Like, is this gonna turn people off? Kind of like the John getting 20, is the John getting 20 front-end equations gonna happen?

**[00:35:10] craftinpark:** no actually I don't think that's gonna happen because we've already been using AI to help us create the question. No, no, no, I don't think so. If I, if I saw like a backend question and it's

**[00:35:17] chdany12:** No, as in like not the AI part, but I'm talking about like, is people gonna get turned off because they're not gonna have any problems that's relevant to them? That's my question. Okay.

**[00:35:33] craftinpark:** like using a mock Uber eats, the, the, probably the core workings of the five to 10 file example, and also like the bugs that have been injected are general enough where I would get value out of it. Yeah, honestly, that person is probably going to be tested on like their like detail

**[00:35:51] chdany12:** Okay, then that's it. We're done. We come to a conclusion.

**[00:35:57] umiclon:** who only focuses on frontend and they like get 10 backend questions, I feel like that's not the type of user we're looking for. I feel like if someone only focuses on frontend, they're more so looking to improve their UI UX skills. So everyone else will probably find the general backlink questions

**[00:36:23] craftinpark:** of like I or like creative aspects at this point but let's go fast like maybe like for the next

**[00:36:32] umiclon:** somewhat relevant to their skill set. We can still make one, more like a random one and

**[00:36:38] chdany12:** Okay, so what I'm realizing, I think so.

**[00:36:42] craftinpark:** meeting our goal is to actually have the questions done I'm wondering yeah should well here's a

**[00:36:47] chdany12:** Yeah, it kind of goes back to like what we said we're gonna do until Thursday. Let's make 10 backing questions each.

**[00:37:01] craftinpark:** thing would that slow us down because there's going to be like but even even this or like

**[00:37:05] chdany12:** You're right, let's make one each. And then, no, because we're gonna have to test them.

**[00:37:11] craftinpark:** Like, for me, making one each, I'm okay with that.

**[00:37:13] chdany12:** Like Dave is gonna test John's

**[00:37:15] david_hong:** Mm-hmm. I think we should do step one as making one question and then

**[00:37:15] chdany12:** and John is gonna take Roger's. Roger is going to take David's and I'm not going to do anything because I'm not a backend engineer. I'm going to suck my thumb. One east and then test it and then we test it once for each other and

**[00:37:31] umiclon:** see how it turns out.

**[00:37:37] chdany12:** then because you guys are all like going to be able to solve this and then we get a quick survey out of it about like what worked what didn't and then we get to four guinea pigs or something and then that's kind of like our value test, no? Isn't that good enough? Or do you want to just like make three one each and then just go to this guinea pig straight away? Yeah, I think we should try to be like the user's perspective, because the only thing

**[00:37:58] david_hong:** testing of each other, and seeing what defines a good question. I think we should all try it.

**[00:38:00] umiclon:** Yeah, the internal test first.

**[00:38:09] craftinpark:** There's nothing too wrong with it. I don't know if that's more efficient than just one person making the questions and then everybody help for real reviewing that question. One person would just create like three questions and then we all chime in like we have a call to like make sure like your question two doesn't have like this most important element we talked about or something but like I don't I don't mind if we just all create one question.

**[00:39:01] chdany12:** that the user is going to see is the question quality, right? So rather than like everybody like seeing John share his screen and like code something, I don't know if that's what you meant, but that's kind of what I understood. I think the fastest way here is just each one of us trying one of each other's questions. And then I guess relevant? Was it good practice? Was it the right amount of time difficulty? What else?

**[00:39:48] craftinpark:** Oh wait sorry maybe we should finish this thought sorry I'll just like say it after.

**[00:39:58] chdany12:** Yeah, John, you don't want to do this? You don't agree with this?

**[00:40:03] craftinpark:** Well, I'm also thinking about like, we need to do it under one repo, right? So we're getting actually practical about this. And if we need to understand the repo to a certain extent, to make the AI come up with a question that fits the structure of what a problem is, I'm okay with it if everybody like make sure that they're not like going like super vibe code mode where like approve approve approve but like they're gonna actually have to understand like we need to come up with some common structure or we can go or we could like all make three different repos but i don't think that's what we're going for right right but like if we

**[00:40:51] chdany12:** Can we just make three branches? But that's something that we can't test, like we can't

**[00:40:55] craftinpark:** don't the current the current repo um barely has an understanding of like what an example is like right now it's right now it's a source folder for the problem files and yeah that's why i actually wanted the you know the page for the defining the problem um to be more to be less of like a discussion page but like an actual criteria of what example is because yeah sorry like a problem right now is like a source folder and then in my repo there's like a public dot json and then the public dot json has a specific structure right but i'm sure like the example that david created has like a completely different structure of like organizing examples

**[00:41:48] chdany12:** decide whether testing whether something's better or not, right? The only way we can test whether whether Davis' thing is better, or John's thing is better if we get feedback.

**[00:41:58] craftinpark:** well i'm not talking about i'm not talking about how the questions look to the user

**[00:41:59] umiclon:** Probably.

**[00:42:02] craftinpark:** i'm talking about how we keep track of each example and like what is the structure like like think about it we need a folder where like we have example one example two example three and they those three could have come from like all like four examples right for each of us but then if each like uh you know object in the folder is like a different file extension then we'll have like massive conflicts right like if our examples folder if our example has like

**[00:42:35] umiclon:** Yeah. It's probably easier to have three repos

**[00:42:39] craftinpark:** my example in a tar file, and then David's is in a folder format, then I think we would have also made changes to the running of the backend for read code to interpret the example. One is only going to work with one specific type of example. In order to do this, we need to make three

**[00:43:08] umiclon:** and just generate three different questions so that we can quickly test and define a good question, because that's our focus right now. The fastest way would be to just create three different. And then later down, when we're trying to work on the pipeline, Before we started making a pipeline, we could figure out what the structure of the shared repo would look like.

**[00:43:36] chdany12:** Yeah, I agree with Roy. I don't know, I find that way more efficient than trying to decide on a temporary structure

**[00:43:40] david_hong:** We should focus on the quality of question first, and the offset of that would be we would actually

**[00:43:48] craftinpark:** three different repos. In order to focus solely on the quality of the question

**[00:43:52] umiclon:** Yeah.

**[00:43:54] craftinpark:** and not the structure of examples, we need to make three or four different repos.

**[00:44:03] david_hong:** have to meet in person on Thursday because we have to give each other's computer to actually try running the test and questions. So on Thursday, we would have to meet in person.

**[00:44:17] chdany12:** which is bound to change depending on the results of our question. Yeah, sure.

**[00:44:21] david_hong:** Didn't the Roger have mother's birthday or something?

**[00:44:23] chdany12:** Are you doing something on Thursday?

**[00:44:24] umiclon:** Wait, can't we have the code run like we just shared?

**[00:44:31] chdany12:** I mean, you can just share the repo and then just run it.

**[00:44:33] craftinpark:** Oh, I can't make it this Thursday, actually.

**[00:44:38] umiclon:** Yes. Like, why do we have to do it in person? Like, if the code, like, can't we share, like,

**[00:44:44] david_hong:** Because the repo is different. And unless you host it, unless you host it, right?

**[00:44:47] craftinpark:** Oh no, it doesn't have to be in person.

**[00:44:48] umiclon:** to run it locally, host it locally,

**[00:44:57] david_hong:** Right.

**[00:44:58] umiclon:** and run it locally and test it.

**[00:45:01] david_hong:** Okay, then let's just do John's repo and everyone just branch off but then just try

**[00:45:02] chdany12:** But I understand that having three repos compared to just having three branches of like three private like three forks of john's thing and just question like testing the question is that what we did already and why do we need three separate repos like you can just change everything that john did on his and then just delete it after we say we don't like it just not yeah this is such a big problem that's am i also doing good can you make one that

**[00:45:23] craftinpark:** Yeah, sure. I think the only problem is like my repo has like a specific way that examples are structured. And then I think in order for you guys to come with examples, you guys are relying on the LLM to understand how the repo has worked.

**[00:45:42] umiclon:** Yes, fun question.

**[00:45:44] craftinpark:** That's fine with me.

**[00:45:51] david_hong:** to use the format with his platform, I mean, code base. And then we could just... Yeah, we shouldn't be boggled on this. That doesn't matter. Okay, let's all use John's repo then. And then just make branches. I think there's no problem with that.

**[00:46:10] umiclon:** I think what Danny says, as long as we mix the branches, we can, even if we create really different examples that might change the code, this is just for a test, we'll get rid of those branches. We're not gonna be trying to combine with all these right now. We're just trying to generate questions right now.

**[00:46:35] david_hong:** Okay, I think we're set. Just use John's repo. We branch off, make our own questions. And then on whatever, Thursday, whatever, we can just go to different branches and check out. And then see each other's questions. right yeah I think she'll still do it like you could we could maybe I could

**[00:46:53] umiclon:** Yep.

**[00:46:59] david_hong:** maybe I could maybe I can make one for you where it's super easy but you still have to have a basic understanding well I like basic as in like okay maybe you could do like a couple hours of research I'm back in okay I'll make

**[00:47:15] chdany12:** bro make me a make me a pytorch question because like whether it's a good question

**[00:47:16] umiclon:** I thought, I thought a little bit.

**[00:47:22] chdany12:** or not it's going to matter, right? And then like when we're talking about when we're going to like

**[00:47:23] david_hong:** you a pytorch question so I'll learn a bit of pytorch then because

**[00:47:28] craftinpark:** Wait, guys, can I get a reminder, why would it be better for each of us to make examples and just one person just make five?

**[00:47:38] david_hong:** Because by having each person make examples of their own, they could have their own flaws and they could have their own advantages and we could see from that, if one person makes all the questions, it's not going to be as diverse as when all of us make questions. And because all of us make our own, we could see, okay, what is a good question is what is a bad question.

**[00:48:03] chdany12:** discuss about what the good question is anyways we're going to use human language but our human language is inadequate and the best thing we're trying to do is compare what we think the ideal questions are, right? So I think the fastest way is to for us to make our live with our limited understanding what what we think the ideal questions are and then by having our peer evaluate them. We can quickly iterate and see the like the flaws and strengths of all of our ideas and then we can quickly make a format of a good question. That's what my that's what I thought

**[00:48:33] david_hong:** Yeah, I think so, yeah.

**[00:48:36] chdany12:** was. You're scared because like your your plot has a lot of rules and like creating sources

**[00:48:37] craftinpark:** Okay, okay. When you guys fork off my branch, maybe it raised a lot, because I feel like, yeah,

**[00:48:52] chdany12:** and stuff right? Okay but if they have like a strong idea then it's essentially just going to

**[00:48:53] craftinpark:** and then the LLM is gonna attach to that. And then the diversification we want is not even gonna happen. Because I was actually very glad to see like David's example today. And like, there were like a bunch of like, buttons for like difficulty and stuff. But like, I'm afraid like, if you guys fork off my repo, like, we're not gonna get that kind of stuff.

**[00:49:23] chdany12:** look a branch but I'm pretty sure it's going to like look completely different so So at least, yeah.

**[00:49:27] craftinpark:** Okay, yeah, yeah. Yeah, you guys are competent.

**[00:49:30] david_hong:** I think what John's worried about is future structure and how we might look at that current structure and then maybe, but I don't know where I'm going with this, but the main question

**[00:49:43] chdany12:** I think John was just worried that AI vibe coding is just

**[00:49:45] david_hong:** is, but we're going to somewhat hand make it, so would that be a problem?

**[00:49:47] chdany12:** going to secretly follow the rules that he made, and it's going to fixate on the problem instead of creating real diversity.

**[00:49:53] craftinpark:** yeah yeah should we do this but before Thursday like I guess David or came up

**[00:49:58] chdany12:** No, it's not. It's not. We just need problem.

**[00:49:59] david_hong:** Yeah, I agree.

**[00:50:00] chdany12:** I just want to see what you guys think the ideal questions are, and if we're going to roast each other, and we're going to do great.

**[00:50:11] david_hong:** In terms of how we're going to build those questions, should we set structures in terms of we have to have a question, we have to have a difficulty for that question, we have to maybe provide hints to it, maybe we could provide other stuff, or what's our guideline for creating a question? Is it going to be very flexible?

**[00:50:29] chdany12:** Oh, this is kind of like what we said. So it has to have an objective answer. It can't require like an open-ended question because actually, yeah, it can't have an open-ended question for now because we're trying not to have an 11 grader. It has to be, it doesn't have to be runnable. It has to have at least five or ten files you can navigate. And let's set a time. You should design it for how long? Yeah, and just give me a back-end question, whoever's doing it. I feel like that's totally fair. I'll just learn.

**[00:50:55] david_hong:** I think a reasonable would be like, if we're going to test it among ourselves, maybe like 30 minutes. 50 would be too long and it has to be like okay I'll give you I'll give you back should we should we assign each other or oh I guess we're all back and so maybe we can maybe we could also think about like oh maybe I could do one for Roger and give him like a medium or a hard one and then maybe I could give it to Danny where it's an easy one and then maybe John could have like a a medium one. Maybe we can... Sounds good. Right. I can maybe... No, no. I should look

**[00:51:31] chdany12:** Okay, let's do by 8, so John's gonna give it, so Danny's gonna give it to John, and then, wait, John's 01, Roger's also 01, right? Okay, but John's birthday is way before Roger's, because John's in January, and Roger's in November, and then like this, okay?

**[00:51:48] umiclon:** Yeah.

**[00:52:00] chdany12:** So the difficulty is dependent on who you're sending it to. So the Thursday, the Thursday result is Thursday results is questions made or questions solved.

**[00:52:13] craftinpark:** with an example yeah I might have to I have I might have to like meet at like

**[00:52:18] david_hong:** into it a bit more. How about we make it by Wednesday and then we give it to each

**[00:52:28] chdany12:** Honestly, question solved is the most efficient because we can get together and talk about our findings. Okay, what time by Wednesday? Let's say 5 PM.

**[00:52:42] david_hong:** other on Wednesday and then once we meet on Thursday, we could talk about it. You You have to send the question by 9 p.m. on Wednesday? No. Is that too late? Are people actually going to do it?

**[00:53:02] chdany12:** Everybody good to meet on Thursday online? Or I thought Roger was not.

**[00:53:02] david_hong:** People are actually going to do it at 5 p.m. and then you can solve it before the meeting and then write feedback. I, if Roger has to meet at 9 p.m. because I think it will work perfectly fine.

**[00:53:13] chdany12:** If that's the case, we can just meet on Saturday, right? Online.

**[00:53:17] umiclon:** John, did you, John, did you say something about Thursday earlier?

**[00:53:25] craftinpark:** 9 or 930 and Wednesday I'm available 9 okay so yeah I don't want to like

**[00:53:27] david_hong:** I could do 9.

**[00:53:35] umiclon:** Yep.

**[00:53:35] david_hong:** You could also do that. But like, it would be better if we met earlier than Saturday, because Saturday is too late.

**[00:53:41] umiclon:** We could have, what if we closed our like forums?

**[00:53:41] david_hong:** Okay, let's do nine then.

**[00:53:41] chdany12:** Okay, and how about questions made by Tuesday,

**[00:53:46] umiclon:** Or, okay.

**[00:53:47] chdany12:** we get on Wednesday, questions solved.

**[00:53:50] umiclon:** Yep. That works. That works.

**[00:53:56] david_hong:** Okay, Tuesday.

**[00:53:57] umiclon:** Fine.

**[00:54:01] chdany12:** And then please bring a five minute speech on what you solved, what you liked and what you didn't like. Okay, two minutes.

**[00:54:15] umiclon:** Yeah.

**[00:54:15] david_hong:** What do you mean one-one?

**[00:54:18] craftinpark:** jump the gun but like if I'm I'm expecting like there's gonna be like a a lot of different opinions. Are we going to consolidate this into one, one? Like, cause we're gonna have to do that at one point, right?

**[00:54:39] david_hong:** I think in terms of making the question, we should be as creative as we can.

**[00:54:39] craftinpark:** Like one kind of, one structure of the question.

**[00:54:44] chdany12:** Oh, we'll see.

**[00:54:50] craftinpark:** No, yeah, I understand. But like, I'm talking like after, after we meet and we give our speeches, there might be like, oh, actually I like LLM grader, or actually I think there needs to be objective, right? So will we be deciding on like a singular format going forward?

**[00:55:11] chdany12:** We might, I mean, I think what we're gonna learn is that there is gonna be what shows us what a weak question looks like, right?

**[00:55:19] craftinpark:** What a weak question, right?

**[00:55:21] chdany12:** Like what a bad question is. So all we do is, if there's five types of questions and they are all good, then we just use five.

**[00:55:31] david_hong:** No, I think we should, we should.

**[00:55:32] chdany12:** We don't have to live.

**[00:55:33] craftinpark:** Well, but like that's not possible, right?

**[00:55:34] david_hong:** But like, it's just questions.

**[00:55:36] craftinpark:** Because we all forked. Like we're gonna have to like, we're gonna have to migrate our examples somehow.

**[00:55:45] chdany12:** Yeah.

**[00:55:45] david_hong:** You don't have to like merge these branches together. It's just questions.

**[00:55:50] craftinpark:** No, like, okay. So there's gonna be like a different form of a question, right? Like your, my LLM came up, like when I talk with the LLM, we decided the best structure of storing these questions is, A, it has like a file structure for the files. And then it has another file, but it also has public.json.

**[00:56:15] david_hong:** I think once we do the questions, make adjustments to the fork, and then we determine what a good question, bad question is,

**[00:56:15] craftinpark:** And then the public.json is in the, it's like structured, right? So it's expecting the first thing in the file to be like the title of the question, right? But then your LLM is probably gonna do something very different. And so if we want to port all of our examples to live in the same repo, then there's going to be huge merge conflicts and we're gonna have to do some migration process.

**[00:56:49] david_hong:** we should kind of rethink about what our structure is actually going to look like. Yeah, I don't think that's the problem we're solving right now.

**[00:56:57] craftinpark:** Right, and then we'll, so yeah, basically we need to consolidate and make a single one rather than have like, but yeah, so,

**[00:57:03] chdany12:** You're concerned about like the website breaking, right? Here's what I think.

**[00:57:10] david_hong:** Because in the end, we're not going to use John's repo when we're building our good version. Like, we should think about the way we're going to structure our code base, and we're not going to rely on John's code base as our foundation, right? I don't think that would be hard.

**[00:57:29] chdany12:** Let's say David comes up with a really good problem that everybody likes. And let's say John, you come up with a problem that everybody likes, right? But they are like different types. John's doesn't compile, it doesn't have running, but it's still very like theoretically really really good practice. But Davis has like that uber eats example and both are really good. Then the value is eminent and then now the bottleneck is tech, right? So we just have to somehow find a way so that they can live together within their repo. This is up to you.

**[00:58:00] david_hong:** I agree.

**[00:58:00] chdany12:** Yeah, this is up to you guys. And we don't have to, we don't have to do that. Like we don't have to think we don't have to think about this right now like i think the the the important problem is this of course we're not gonna have like of course it's not viable in a sense when we have ten hundred thousand different types of problems and like they're all gonna have like a different format we're gonna have to do some consolidation at this point but we shouldn't try to solve this problem right now yeah so let's talk about it after i mean

**[00:58:31] david_hong:** Yeah, exactly.

**[00:58:36] craftinpark:** but like after our meeting, that's the next thing we're gonna have to do though.

**[00:58:43] chdany12:** We might find that it's actually more.

**[00:58:44] craftinpark:** Okay.

**[00:58:45] david_hong:** John's so technical. He's thinking about the future.

**[00:58:51] craftinpark:** No, like I knew that we were gonna do this after the meeting. It's just like, I was like wondering if we understand there needs to be a consolidation.

**[00:59:00] david_hong:** Yeah, I believe we do.

**[00:59:05] craftinpark:** Yeah, okay.

**[00:59:07] chdany12:** Okay, then, uh, okay.

**[00:59:10] david_hong:** Let's meet on Wednesday, 9 p.m. Okay, that's good. Have a good night, everyone.

**[00:59:15] craftinpark:** All right, sounds good.

**[00:59:20] umiclon:** Yep, good night guys.

**[00:59:20] craftinpark:** Yeah.

**[00:59:22] chdany12:** John, no workout tomorrow, okay?

**[00:59:24] craftinpark:** Oh yeah, yeah, I'll probably go alone. See ya.

**[00:59:30] chdany12:** See ya. Bye.
