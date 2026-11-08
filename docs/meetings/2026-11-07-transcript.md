# Meeting transcript (craig-Wmxf6iUoJa4b-_mQNw2tB7I65IrbsAiOJF5cPK6XAPf.flac)

```
Recording Wmxf6iUoJa4b

Guild:		ReeeeeedCODE (1563041544725078088)
Channel:	Meeting Room 1 (1563041546364911617)
Requester:	chdany12#0 (297713772200460288)
Start time:	2026-11-08T04:09:44.495Z

Tracks:
	chdany12#0 (297713772200460288)
	craftinpark#0 (185848419967827969)
	umiclon#0 (659600931632971810)
	_david_hong_#0 (602310736873783317)
```

Transcribed automatically with Whisper `medium`; names are Discord handles. Expect misheard words, especially names and jargon.

**[00:00:01] chdany12:** Okay, there we go. Okay. Sorry. Sorry for interrupting go John. Yes

**[00:00:11] craftinpark:** Oh, no problem. OK, let me show my screen. Can you guys see my screen?

**[00:00:40] umiclon:** Yes.

**[00:00:40] chdany12:** Can you so what does this make currently if you make the questions? What's the reason behind that? Oh, I see what you mean

**[00:00:43] craftinpark:** OK, so basically, we have it so that we can classify a job description. So the job description is just a string, and it gets classified. And then right now, this function, I guess David also didn't see this, but it just creates a plan. The reason I separated the plan from the pipeline is because classifying also takes money to the API. And you can create a plan once and then keep making examples. So if we combine it into one step, then we're going to have to classify every single time and it's a waste of money. So I just put the classifying and the plan making part in its own function. But really, it's part of the same pipeline. So it classifies. And what this plan is is it just gives you a list of how many examples you need per concept. And so the taxonomy is like, I think we talked about it last time, but it's like the list of concepts that we actually consider as a concept. And so for a given job description, it might choose deadlocks need three examples. And retries and back off needs two examples for this. And in like machine learning terminology, we have a couple like hyperparameters. So I said like, you know, the top postings, I think like one example is like too little. So the planner makes it so that, you know, even the topics that aren't very primary to this job posting. If you're gonna have an example, you need to have at least two. And then the share power, it's very technical. I'll just go over like really quickly. Like 0.6 as a weight is more, it really is more than double the significance of 0.3, right? Like as a just a fraction, 0.6 is twice as much as 0.3. So if you get a weight on a topic that's 0.6, that actually means it's significantly more prevalent than 0.3, because a lot of things have 0.3. So we just power the two before we combine it. And so the power itself is like a parameter, because it's involved with tuning. So the share power would go in. I hope that makes sense. And then I just set the examples for posting as 20. And then, so that's the plan. And then the pipeline, right now it doesn't consider what examples we already have. Me and David just set it so that it chooses the top weight. And yeah, in order for us to focus on the domain side, we simplify what an example is quite a lot. And so even though we decided that an example would be runnable, us actually running the API started costing us money using the Cloud console. So we were using David's credit, like $5, and then I also set up an account, so now I can start using the API. But for the sake of saving costs, the format of our examples has just been simplified to four multiple-choice questions. And then the three multiple-choice questions are related to, like, explanation. And then the last one is the bug. But the bug is in the form of a multiple choice question. So we definitely need help in the front of, like, refining what an example is. We just went completely all out on the domain. Does it make sense to everybody? I do have a rudimentary front end. Oh, it makes a right. So the example is an object of three portions. The public JSON file has information about the title, when it was made, and the actual questions. And then you have the key file, the answers to the multiple quick choice questions. And then you have files, which are like the content file and you have the path in the in the folder structure that it would be like represented to the user and so you can see here well this one's a little bit outdated but the Trilio example follows this structure so we have the public JSON just like here key JSON and then you have like a bunch of files under I asked Claude to make something very rudimentary. Yeah. And right now, we went away from an open source repo. We're just having AI generate the code. So I think there's a trade-off between whether we use open source or we make the code runnable. Obviously, even with the AI generator right now, our code is not runnable. But I think it would be a lot cheaper, at least in theory. Maybe it's wrong in practice. But in my mind, it's harder to make an open source repo runnable because it might require the AI to go through the entire codebase to see what's missing. Yes.

**[00:07:54] chdany12:** So you're when you mean by open source, you're not talking about Grabbing problems small resource You mean like like having the whole open source being like runnable, right? so because what I what I what I thought was

**[00:08:10] craftinpark:** I think for our first example generation phase we did, I made an example using bollmq and

**[00:08:12] chdany12:** just cherry picking common problems you can find from instead of like having the whole repo as your problem. I think there's two differences right then you were just this is a clarifying question you were against like you're not against cherry picking but you're against like having the whole open source system as like the question is that correct by API I think you guys are

**[00:08:55] craftinpark:** it only needed five files to cover queues as a topic. But then I think if we actually instructed, like, Claude to scrape the necessary files to create your example, but we need to make it runnable, then it might go from the five files, but then it will go into, like, another file and say, okay, I need this if we're going to make it runnable, and then I need this. And then the cloud might perverse like a hundred files and that might cost a lot of money. Like the kind of money we're talking about, I think me and David got it down to like less than 50 cents per example, but then, yeah, it's not bad, but like it actually is a concern if we're talking about like hundreds of examples.

**[00:09:52] david_hong:** Yeah, yeah. The API keys are different from Claude Pro. Well, you have to you have to use the open API key because when you're giving the job description to be able to read that job description string and to be able to determine the weight of that's where we need it. Yeah.

**[00:09:56] craftinpark:** And I think if we make it runnable with open source, it might go up, sorry, no,

**[00:10:03] chdany12:** causing costs by like just the tokens not like actually you guys aren't using separate money to like more than a subscription right you're doing api keys yeah why do we need why sorry i don't

**[00:10:12] craftinpark:** Yeah, so there's actually, you can write code where every time you need to call the API,

**[00:10:28] chdany12:** know can you help me understand why we need api keys i don't think i understand

**[00:11:00] craftinpark:** you can like port it to an open like cloud web, but that's a, I heard it's a legal gray area. Yeah, no, that's basically it.

**[00:11:09] david_hong:** Something that we realized is like the amount of the pricing and like the tokens that is used when we're using cloud.com versus the API, the API is like much more expensive for some reason.

**[00:11:27] chdany12:** api's are much more expensive yeah that doesn't sound very scalable to be honest

**[00:11:27] david_hong:** Yeah, so that's like our concern because like if it's 50 cents per prompt, then it's like, what, like if it's like 100, that's like $50. So I don't know if it's scalable.

**[00:11:47] chdany12:** I think because the non-APM... Okay, but this is not the important thing. Let's listen to... Sorry. I'm dragging you guys off with the tangent. Can we finish what you were trying to say, John? Okay. I can quickly talk about what Roger and I did.

**[00:12:06] craftinpark:** I think our sore spot right now is in the attempt to get this to work. example is kind of not very valuable in terms of the questions. I think I haven't really sat down and saw how good the multiple choice questions are, but I was kind of discouraged from doing that because I feel like it's not as good as, you know, like a tailored example that we've made in the past. And then just to close us off, I think the next step in terms of domain side is instead of just, you know, choosing the top label, we just track which examples we've already made and then we go for coverage. So if there's enough examples in the bank, then the pipeline will stop running, basically. That's everything. Yeah, yeah. And then also, oh yeah, sorry, I think one thing

**[00:13:11] chdany12:** So we tried to solve a bunch of problems. Not a bunch. We solved two. And they were supposed to take an hour each. hour each. But there were problems that I created that was supposed to like it failed on all three opus problems. Like opus couldn't solve it all together. One of it was like a muon detector and like it's kind of like an engineering software kind of debugging problem. It has like a muon detector and like if it tries to like get something from the sun and AI is not able to solve it. Another problem is like, you're kind of like, what would you describe that question, Roger, MVP 14? What would you call that?

**[00:14:01] umiclon:** Optimization.

**[00:14:06] chdany12:** It's like threading, yeah.

**[00:14:08] umiclon:** Yeah.

**[00:14:10] chdany12:** So there's like threads and you have, there's like a batch and you have to like make sure that the process times like P 99% is like, it's like if you have too much of a batch, and your threads are like, it's like a balancing problem. And that like failed. I tried solving it with AI, I wasn't able to solve it. Roger also tried to solve it with AI, he wasn't able to solve it. And I tried three fresh agents trying to solve it, it wasn't able to solve it. But the takeaway from my side is this. Number one, AI-proof problems can turn into guessing games if we're not careful, and we still haven't tested whether this is a goal worth pursuing or whether it's even feasible. Because when I tested it, it just seemed like you were able to get away with getting the question right or wrong even without understanding the context. So the reason why things get, AI gets things wrong, Oh, what? There's a guy screaming. Sorry. I think there's a guy screaming outside of my apartment. Anyways, yeah. So the AI struggles with it because you're only given like 10 tries and then within the 10 tries, you have to like read, you basically have to read what the system outputs and it's kind of like a balancing situation. Like if you increase this part of it, then like the cores are getting throttled too much and it was like basically a sort of like a problem. But to me, I was able to solve or like try to at least attempt solving this problem without understanding like what threading and like core management and those things is because it was just like a guessing game. Like I could just, even without knowing any context, I could like improve, try like doubling, like there's three variables and then there's a result. And then all I understood from this context is that I want to get this result to 40 instead of 20. And there's three knobs that I can, three levers that I can change. So that was like just using common sense. I was moving all the levers and essentially that didn't really help me teach anything about backend programming. But yeah, so what I learned from this is that the type of things that AI can't solve is we found things that AI can't solve. need to give something that's like a real system and the instrumentation is not perfect so the data that comes out of it is very limited and you have to have a lot of like compromising and a lot of like what do you call it like if you yeah like a lot of balancing problems but that like that is like a totally different question to whether this is useful for a software engineer, that's what we realized. Yeah, so that's all the take-aways. And it does take quite a, like, and the muon question, both Roger and I got it right with using AI. That one, there was a loophole that we found, but it was still like, also very, very guessing game-like. I don't know, what did you think Roger? So my proposal is that we fold this branch of exploration.

**[00:17:48] umiclon:** I kind of made like AI Cloud do most of the work. Like I just asked it to do a bunch of tests. Like just run a bunch of tests on one of the levers and see what the results look like and then use the best value and then repeat for the next lever and the next lever and then like just fine tuning and hoping that the the result is the it passes the final test. I can see how it like it could help like make someone better at using AI like understanding tests and running, like being better at like giving prompts to AI, but in terms of like the software engineering principles, I'm not really using any of that.

**[00:19:09] chdany12:** I think we should just focus on like whatever like we choose one branch of the domain and then we try to make the multiple twists or whatever like open like free response questions and then we all we should solve it and just tailor make one like we should just make we just trust out test out John's like or John and David's pipeline try to solve it and then talk about why it's bad and then improve quickly I think that's the fastest way I think AI and like augmented problems is a little out of scope right now I'm realizing that that it's a lot more research than I thought it was.

**[00:19:58] david_hong:** Yeah, I think the thing about our pipeline that John and I created is that we're really focused on like how we're going to operate the pipeline, but we didn't focus a lot on like the prompt where it asks to create the examples because like the how to create the examples like that wasn't what we explicitly asked like we didn't hand write the prompt for that it was a lot of just like oh how are we going to structure data how are you going to store data right so in terms of that that's why I think the examples that we generate right now aren't going to be the best and we need to do something about that so our is our entire goal such that we first of all find out why it's bad

**[00:20:41] chdany12:** But that's good. It's good that we have the worst of problem is that we're all gonna have an idea about what it is, right? So I feel like we should just all go to whatever branch that John made. Like if there's like a problem and John's gonna, like it's going to be able to create a runable file. I mean, or ideally at a certain point, Like we're going to be able to give it a job description and it's going to tailor make some sort of runnable small source file for us. But you guys are saying that the multiple questions are going to be shit, right? So then what we need to do is try to solve the questions of the multiple choice, write down why it's crap and then make three questions that we tailor made that I think is a better response. That's the fastest takeaway that I think we can do from what we have currently.

**[00:21:48] david_hong:** Second of all explain to them why how we can make better and as a result We'll create like one good prompt that we can use for the API key such that it creates better examples that we want Is that our main goal?

**[00:22:03] chdany12:** Yeah, we need to find out. We're basically doing the same question. We're finding out what a good problem is.

**[00:22:07] david_hong:** Right, right. We need to

**[00:22:08] chdany12:** And currently, our current problem is that it's not,

**[00:22:12] david_hong:** Iterate the problem

**[00:22:14] chdany12:** you guys aren't satisfied with the questions, right? Because we didn't do anything about it.

**[00:22:17] david_hong:** So, wait, so your idea is to avoid using API keys and try using our Cloud Pro instead?

**[00:22:19] chdany12:** And one thing I'm, sorry, go ahead.

**[00:22:26] craftinpark:** we also hit is like the, um, the cost. Like we, I think me and David were going in with the intent to make it runnable. And then we found a new problem, which is the cost. And it's like a very like pragmatic problem. And we might have to come up, we might have to like decide as a group, like what is the upper bound on like the cost per pipeline. like maybe something like the max for a question is like one dollar and if it's pushing up over $1 and like it's going into like unfeasible territory I don't even yeah I don't even know okay okay yeah that makes sense yeah maybe then

**[00:23:17] chdany12:** I think for this case, I would like to remove that requirement at all. So I pragmatic approach here is, like John said, like what our company does is that we realize that the API that is actually really required is much more expensive than a seat, right? Like that's, we can all agree on that. Like we paid $30 for a month and the amount of tokens we get, if we all converted that into API, that'd be so much more worth than, like worth so much more than $30, correct? Yeah. So what we should do is we should separate out the requirements and the solution. The solution is one of the requirements is that we want to give tailored problems based on the job description, correct? And one of the solutions that we came up with is putting an API key with an LLM so that the LLM parses it live and then creates questions, correct? Because each question is 50 cents, it might not be feasible, at least for our first version, right? If we have a subscription model, then that might become feasible later. But at the current rate, it's not feasible, right? We want it to be free. At least that's what I'm assuming. So what we should do is we should have, like, use basically subscription max, our problem right now, and either get a separate Gmail, pay $30, and then just have it constantly running to create a database of problems, and then just have a more static job description parsing to already pre-made question sorting algorithm. I feel like that's the way more version 1 level scope-cutting solution. But of course, this is another solution. It's not the requirement. So if you have a better solution that's faster and keeps our requirement of satisfying as much customers as possible, then I'm all ears. But you can also challenge the requirement. But the requirement isn't that we have to satisfy 100% of our customers. It might not be. It might be only that we only have to satisfy 70%. Kind of like what Roger said, like if he's getting a job description for this specific role in his backend, and he wants to learn about queues, but there's no queues, but there's like other stuff about backend, then he's still willing to come back to those websites. That's what Roger said, right? So the requirement may not be that we have to 100%. Like it is a pain point where somebody comes wanting to learn about backend and having finding no questions about backend. That's a failure point. But if somebody comes specifically about this specific backend team or this specific company, but they're not finding that tailor-made problem, but they're finding problems in like the neighborhood, like K&N, like that might be the real requirement. So I think we have to talk about what the, hone in on what the real requirement is. That makes sense. I don't understand what, how that has, how does that relate to the

**[00:27:07] craftinpark:** let's like uh let's uh rip apart this question was right now it would be

**[00:27:20] umiclon:** How feasible would it be to have AI grade its own examples? Like we make it generate examples and then we create the examples feed it back like so that it knows like it has examples like a number of bad examples a number of good examples and it can create better and better examples every iteration every time it creates a new example or are we trying to like create like decide on a what a concept example

**[00:28:00] chdany12:** topic that we're talking about right now. No, currently we're talking about the price,

**[00:28:14] umiclon:** is right oh I see yeah yeah that wouldn't be you mean and during their

**[00:28:21] chdany12:** like what are we going to do about the problem of each problem, that when we parse it, when somebody comes, let's say this name is Bob, Bob has a job description and then give it to our website. The API is going to take it and he's going to parse it and Taylor make questions for Bob, but that's going to take 50 cents. If he makes 100 problems, that's going to be $50. So that's unfeasible currently because we don't want to cost 50 cents. So that's what we're talking about on the API. Okay, I mean if anybody is against my idea, let's sharpen some

**[00:29:07] craftinpark:** like optimistically I think like the question took 20 cents so making 20 questions would be four dollars but then we gave it every way out like it only had to do multiple choice sorry yeah so so yo we can we can run the plan we

**[00:30:04] chdany12:** iron. I was just reading to a Jensen Hwang podcast and he thinks conflict is always a better way to polish ideas. So you should always try to go into ways where your ideas are challenged. So So please challenge my idea or requirements.

**[00:30:30] david_hong:** Right, is to make good examples.

**[00:30:31] chdany12:** Yeah, I think the requirements of this salute, like the requirements of this, like more like the total goal of this product. Yeah, and it's also to like, we wanna tailor make it. Of course that's something that we want, but we might not have to tailor make everything. So with our current budget, like it won't fail. It won't fail as a product, I don't think so.

**[00:30:57] david_hong:** And so, how are we going to base what John made to that next step?

**[00:31:04] chdany12:** Like currently you guys have a pipeline

**[00:31:04] david_hong:** because. Right, right.

**[00:31:07] chdany12:** create something, right? We create problems, but you guys cut the prompt a lot in trying to save as much cost as possible, right? So I think we should take 500 different types of job postings or related to backend and pre-make questions. Yeah, we can get another cloud program. We can

**[00:31:35] david_hong:** Using a lot pro account so are so like once once our

**[00:31:41] chdany12:** can make somebody's dummy email and just make a club program. Yeah, guess who?

**[00:31:48] craftinpark:** could even run the plan on the pro but what the plan will give us is hold on. Oh, I didn't save the plan? That's a 10 cents wasted. Wait, what? No way. Sorry,

**[00:32:09] chdany12:** There's a user, and all the user sees is problem, output, request.

**[00:32:29] david_hong:** Claude Pro generates it, are you thinking about copying and pasting that somehow into our database?

**[00:32:37] craftinpark:** say that again. Yeah, right. So for us to have like a 70%, you know, pool for backend,

**[00:32:38] david_hong:** I'm this is to ask about Daniel's program. I mean Daniel's idea. So once we actually generate something using our Claude Pro account like and then we get the output. Are we going to use the output to put in the database? yeah the number for that concept wait john are we now thinking of doing that thing that we

**[00:33:19] chdany12:** The user gives request about what kind of problem he wants, and then we retake that and then we output the problem, correct? Only two things that the user is going to give is request, problem. So, we have to create problems that is useful and is seducing to the user to come back. And we have to, that's requirement number one, we have to make good problems. We don't know what that means yet. We're trying to find that out. Number two, then this is the requirement, requirement of this whole project. Number two is that we have to accept users, satisfy users desire or request of trying to find a relevant problem. We don't want it where John wants to solve back-end problems and all the problems that we can give are front-end. That's wrong. So it's all about requirement spec-ing here. Do we have to be accepting 100% of the requirements of questions. If they want a very specific back-end problem, and we don't have it, is that going to fail? Is that going to get rid of this? Destroy this whole ship? I don't think so. I do think it's more desirable. That's an evaluation criteria. That's something that's not a need. This is a need. This is a want. So we want to have it, but I don't think it's a need. So it can come later. So, okay, what's stopping us? We can just do this, right? There's nothing stopping us.

**[00:35:18] craftinpark:** I think we should come up with like a goal. Like we talked about, I talked about this David, but like come up with a golden list of 500 job postings that represent the sea of back end. And then, yeah, sorry. Yep, there's nothing stopping us. And then, so I think right now it's

**[00:35:49] chdany12:** Who wants to do this? Yeah, let's just do it. John, you want to do this? And then now the 70%

**[00:35:56] craftinpark:** more about like quality, because we could just ask Claude to do this for us. And And if nobody sees any problems with it, then I'm on board. OK, I'll just ask Claude to come up with the golden list, and then I'll commit it.

**[00:36:22] chdany12:** pool, and then now we have to think about what the 70% pool is going to make, right? And then

**[00:36:30] craftinpark:** Right, so then the 500 job postings will create it. We can make it a single plan.

**[00:36:43] chdany12:** it's going to create n problems. But this n problem is we need a one golden archetype

**[00:36:47] craftinpark:** Yeah, and they'll all have labels for the concept.

**[00:36:59] chdany12:** of a problem to face this, to like clone it. We need the first clone soldier. Or like, you know,

**[00:37:01] craftinpark:** Yeah, right.

**[00:37:10] chdany12:** it could be n types of clone soldiers. Basically, what is a good problem, what is not, right? So and then eventually we also need the sorting algorithm. So if we have n problems, how are we going to match this with the user's request?

**[00:37:32] craftinpark:** So here, I think we can complicate the arrow in the middle. So the 500 postings turns into 500 plans.

**[00:37:56] chdany12:** Well, how are we going to get 70% of the domain of stack and scrape 500 golden list of topspins? Second, how do you change that into problems?

**[00:38:52] craftinpark:** And then the 500, yeah, that's a good question.

**[00:39:00] chdany12:** What is a good problem? What do you mean by that? Oh, the concept? Are you trying to say category?

**[00:39:05] craftinpark:** So yeah, for two, each problem can get turned into a plan. And then the plan says, it's a concept an account for that concept. Oh, account, like a account. Account, yeah, so like a number. Yeah, so we can just do concept, colon, number, or account.

**[00:39:44] chdany12:** How do you define that?

**[00:39:46] craftinpark:** Concept as in like the exact taxonomy label. So for example, like backend dot concurrency dot queues.

**[00:40:05] david_hong:** talked about in the cafe where we're trying to get all the coverage is that what we're trying to do now yeah i see we know how do you know is there a bug is it working

**[00:40:10] craftinpark:** Yeah, yeah. So let's say like one of the plans says the concept queues needs three questions in order for this job posting to be covered. And then we do it. And then let's say another job posting in the golden list says, oh, I also need three questions for queues. Then we don't have to do anything for that second job posting because there's intersection. Does that make sense?

**[00:40:50] chdany12:** How do you define that job posting A needs 10 questions of back-end subject concept B?

**[00:40:52] craftinpark:** Define which part?

**[00:41:09] chdany12:** b but it's like what how does this affect our customer if it fails g what if we our plan makes

**[00:41:10] craftinpark:** Yeah, let me run the... I can't believe I didn't save the plan. It's actually crazy. But let me just... How does this affect our customers if it fails?

**[00:41:38] chdany12:** one question or n minus one questions what is the effect do you guys have an answer to this yeah so what if our plan makes n plus one questions or n minus one questions what is effect. Yeah, so we can be pretty forgetful, but what if our concept makes concept C the job

**[00:42:37] craftinpark:** Not much. So n is the ideal, right? Not much. Yeah. Yeah, that's a...

**[00:42:53] chdany12:** posting which is totally unrelated instead of concept B? This is pretty dissatisfactory. Okay, so this is much more important than this then. So we need to, so we can get wrong by n

**[00:42:59] craftinpark:** That's pretty... That's a problem because it's gonna go like... That's a flaw in the planner and the flaw is going to propagate for every single job posting. Yes. V? Oh, B.

**[00:43:26] chdany12:** n as long as n is bigger than zero. But we should get B wrong, okay? And how do we know we don't get B wrong? That's in the plan. B, like David and John will figure it out.

**[00:43:54] craftinpark:** Well, okay. I'm trying to run the planner right now.

**[00:44:13] david_hong:** I think it should still be five because by having it like more importance that it just

**[00:44:15] craftinpark:** It's running now. I didn't have my API key. So it's going to use like 10 cents hopefully and nothing more. I'll share my screen. So you guys know the taxonomy concept. So this is like, this is supposed to represent everything, by the way, like, if the if the taxonomy is missing labels, then that's the fault of the taxonomy, but then so in order to like mitigate this we also have versions of taxonomy. If we like realize bad about it. This might not be another discussion point. But anyways, using the taxonomy. it makes a weight for every single label and then depending on like the like it went crazy on rest design and say it needs five questions so I'm guessing like the weight for rest design for the Twilio job description was like something greater like 0.95 like the LLM really thought that the the Twilio job posting is related to REST design. And so that's why it comes up with the count of five. But this is basically the planner. And then the consequence is like, for the n plus one, n minus one, I don't see it being too big because that would be like this or like this. If this was ground truth, right? If this was like really what represented Twilio. And then if idempotency was like, it was still significant, but then if this didn't exist and it went to something like tests or something, that would be the B instead of A. And that would be a pretty big problem.

**[00:46:37] chdany12:** How do you vary, or how do you grade this?

**[00:46:37] craftinpark:** So we have, we can't, we would have to like manually.

**[00:46:47] chdany12:** You know, if we can't grade something,

**[00:46:51] craftinpark:** Sorry?

**[00:46:53] chdany12:** that's a red flag, right?

**[00:46:59] craftinpark:** Yeah. I mean, we can grade it manually. So based on this job description, I could go through and say, OK, hold on. This job posting did not actually really talk about queues and consumers. Or something like, clearly it needs testing to be a top concept where examples are made for it, but it didn't make it here. Is there testing here? others in testing.

**[00:47:38] chdany12:** What if John, or let's say some different name, Bob uses this? Here's all our problem. Goes to the Twilio question, and then they ask something completely different. Is that our fault?

**[00:48:07] craftinpark:** The example generated is completely different.

**[00:48:11] chdany12:** It asked a target of the taxonomy that wasn't in it. Twilio asked it.

**[00:48:22] umiclon:** interview you got asked that completely but we can't predict everything that's

**[00:48:24] chdany12:** John, can you pull up the interview did for apple like the gel posting if you had that and if you give that answer does i feel like

**[00:48:31] craftinpark:** Yeah, but someone took my spot.

**[00:48:39] chdany12:** that's the only verification we actually have right you actually need somebody who did this

**[00:48:58] craftinpark:** Are you kidding me?

**[00:48:59] chdany12:** or maybe maybe i'm trolling here maybe i don't know do you guys do you guys say the point that i'm trying to make though yeah i think the problem is do we need to predict if we had

**[00:49:08] craftinpark:** Yeah, I see it. And actually, that's a big risk, because I got asked stuff outside of my job posting. And yeah, the planner is also another one.

**[00:49:34] umiclon:** gonna be asked all right right you can't predict something that's not gonna be asked yeah what do you mean by count five it seems I was wondering and let's

**[00:49:48] craftinpark:** I think we can't not predict, right? Because this one here is our best choice. But then if it gives you this, then that would be that case we went over earlier today where like, right.

**[00:50:12] chdany12:** a good question. Let's say we have like really fantastic questions for this golden list, right? And then the customer just brings in the Twilio text then he parses it himself and then he chooses the questions himself to practice. Like I think that person is still gonna come back.

**[00:50:38] craftinpark:** So yeah, here's my proposal, right? So Quilio, in this case, would be one of our 500. And then let me just duplicate this. So let's say this one is for what's another company?

**[00:51:06] chdany12:** NVIDIA? They must have backend engineers there, right?

**[00:51:06] craftinpark:** Why can't I rename this? Yeah, sure. NVIDIA plan.

**[00:51:15] chdany12:** Okay, so getting from this, John, is that the 500 questions is important for us to create,

**[00:51:17] craftinpark:** Yes. So let's just say this one is testing unit tests or something. So you see how there is commonality in the rest design? Let's say this is 3. So we wouldn't have to do anything for this one because 5 have already been made from the Twilio plan. But then this one would have to be made. And then, probably, if our goldenness is 500, the last 50, we'll probably not have to do anything at all. But we don't have to do that, right? I think the customer will see their

**[00:52:08] chdany12:** to cover as much field as possible, but I think my question is, do we need to have the curing feature? This helps us prepare that we have what they want in our set, in our arsenal, But do we need to create when they bring something, oh, you should solve this, because that should has to be based on something. Yeah, I don't think so. Okay, I agree with that.

**[00:52:51] craftinpark:** Twilio job posting and then let's hope they're smart enough and they realize, okay, I need to be an expert in rest design and so on our website there will be like a directory like where you can find like you'll have I mean it might be more but there will be like rest design hopefully because we put in 500 and probably 500 job postings classified will have cover rest design and so they'll go knock themselves up with these questions but they won't they won't be putting in Twilio and classifying it themselves. I don't think that's required.

**[00:53:37] chdany12:** I have another question, guys. If say 300 out of the 500 questions, 500 job postings, all have backend API rest design, and they all have count five, does that mean it's count five? Or should we have more than five? 500 I think I was just trying to make the point of like if there's so many people that wants rest

**[00:54:15] craftinpark:** Like five examples. Right. Yeah, that makes sense. That makes sense. Okay.

**[00:54:17] umiclon:** But yeah, I thought the account was specific to each individual job posting.

**[00:54:27] david_hong:** shows that it's more important but either way it's just still gonna be like are they really gonna want like 30 questions just on rest design or should we just make it so they could have just a couple to just get the design just get a couple to just get like what do you call it like basic practice down i don't know i i think i think um um like isn't our goal right now to get coverage not just like focus on one specific rest design like you're there your idea is theoretical but i don't think that's gonna happen But like, if those five examples really cover rest design well, like, wouldn't that be enough?

**[00:55:15] chdany12:** design and then everybody has five like the count that the plan makes is five then should we give more than five so people come back but you're right that's like but how many that's like saying

**[00:55:38] david_hong:** But I guess, yeah, it's gonna be hard to do that because rest design is big. Yeah, I don't think it's, um, I would, yeah, okay, yeah.

**[00:55:45] chdany12:** like we need one exam exit uh final exam test practice but we want as much as possible and Okay, but I realized that I pulled us into rabbit hole. This is not important. Somebody will complain if they want more problems and that's a good sign for us. So let's do, yeah, let's do what John will, let's do what John says.

**[00:56:19] craftinpark:** Okay. I was going to draw a diagram, but I guess we can skip it. Yeah. So now, if I'm not wrong,

**[00:56:24] chdany12:** Okay, so what's our next thing? So John will do the 500 scrape. We need to be solving problems so that we can critique them. So we need to get problems in front of us. And the AI using thing is going to be concluded as out of scope for now. So John is going to do the 500 scope. Someone needs to think about how we're going. Actually, we found out one important thing is that we're not going to do a curating algorithm. We're just going to give them a database and tell them to choose for now. So yeah, go, John.

**[00:57:13] craftinpark:** the only thing left is to make our question better, right? Right now we're stuck with

**[00:57:18] chdany12:** Yeah, we don't need an objective way.

**[00:57:22] craftinpark:** four multiple choice questions one of them being a bug how do you how do we rate them

**[00:57:29] umiclon:** How do we grade our questions on the scale of how good they are?

**[00:57:37] craftinpark:** oh that's a good question no i don't think there is i i actually asked a dude from my work

**[00:57:38] umiclon:** How are we going to rate the question? Is there an objective way to rate them? depends on what type of bug is it that John and if it errors you all we can just make that

**[00:57:57] craftinpark:** to like try read code and this guy's like um like no offense time but he's kind of like super like doom scroll like he lost into that like you know but like he like the moment he opened up the code base he's like I'm not reading all that but I think like this is literally what AI has like devolved us into which is like what read code is trying to like help but he's kind of given in and so I did get his feedback but like all of his feedback like I have a big like asterisk on like so I feel like there's like no objective way to rate the question does that Does that make sense?

**[00:58:48] chdany12:** We just need some feedback. Can I show you guys something?

**[00:58:53] craftinpark:** Yeah.

**[00:58:57] chdany12:** So this is another project that I'm doing just on myself.

**[00:59:04] craftinpark:** Oh, I can't see your screen.

**[00:59:06] chdany12:** I'm not sharing it yet.

**[00:59:08] craftinpark:** Oh, damn.

**[00:59:25] chdany12:** It's not this one, this one. Okay, so this is a damage generator that I made with Claude. So yeah, so you can replay,

**[00:59:39] craftinpark:** Damn.

**[00:59:42] chdany12:** just drag and dance and go to attack and then like plus one and speed. And now like, oh, who moves first? And you think it's Dragonite, but it's actually their Garchomp.

**[00:59:53] craftinpark:** Virtual is hella fast.

**[00:59:55] chdany12:** Yeah, but anyways, you solve these problems and then you go to the end. Like this is like another problem that I'm doing. This is like lead guessing. Like it gives you like the draft and then you have to like, you have to like guess what the game was. And like I've been sending this to like my brother and Jake as like a kind of like an MVP and then what you can do is like you tell me how fun was it? Would you play a new one every day? Did the yellow colors help you narrow it down? the clues are too strong and then they say something and then you get an answer and then you copy the feedback and you can paste it like this so so something like this is really powerful for me

**[01:00:31] craftinpark:** Oh, so should we add a survey?

**[01:00:36] chdany12:** because every time i run these ones out like the reason why this looks good currently it looks better than before is because so many people give me feedback like my my brother christian people that actually like pokemon there and then myself also they also wanted like rather than having lines here I want some effects and I want this to have it I want people to like you know to like put their mouse over and get like you know like answers like this and that's like good feedback right so currently what we want is we just want feedback so we should make something like this and just send it up one or two questions that we think is good and then we just have to keep giving it to people and that was I think that that way is like but of course it's harder than this because like people are very willing to play games like this like Christian really liked playing this and my brother was also really excited to play something like this but like like what we have is like we have to ask somebody to solve a problem right yeah yeah so I think that's our biggest problem I think that's our biggest thing

**[01:01:40] craftinpark:** Yeah, and hopefully we do it before we go all in on the 500.

**[01:01:51] chdany12:** here I like that I think every time we do the 70% and we upload this to the internet

**[01:01:55] craftinpark:** How about this then? How about we like this Twilio one? Okay, I'll just finish the sentence even though it's like, yeah. We finished this Twilio one. We just do our best. And we finished the version of a good question today. We spend a week getting feedback on this exact same Twilio one, getting people to try it from the start to the end. And then hopefully that feedback will give us a 70% acceptable clone model. and then we go all in and then we cover the 500 golden.

**[01:02:44] chdany12:** we're going to get more feedback anyways. So getting it faster out there and failing is always the better way here. So I think that's the thing we can do it so I agree. Yeah I mean like the

**[01:02:55] craftinpark:** Okay. So today let's do a mini iteration and just come up with the best question before we get feedback. So three multiple choice or four multiple choice questions. What do we think about that? Should we just make it runnable? Cause we're not thinking about money.

**[01:03:25] chdany12:** that's just like kind of like we all want it to be runnable right? Like when we solved all four

**[01:03:30] craftinpark:** Yeah.

**[01:03:30] chdany12:** of our questions, like when we solved each one of our questions, the conclusion was that it was nice that it was all runnable. So I don't think we should retract away from what we came up with by like swapping all of our problems. I think that should over supersede anything else.

**[01:03:50] craftinpark:** So should we make the runnability Like it's, it's relevant only for the bug question or no, cause you can't run something to understand how it works if it's broken by the bug, right?

**[01:04:11] chdany12:** That is true. Guys, what are you guys doing on Wednesday?

**[01:04:14] craftinpark:** So I'm thinking there's like three comprehension questions but if the bug is still unsolved, then I can't run it.

**[01:04:24] david_hong:** But like, if it's a bug that you produce for a certain action, then the code itself

**[01:04:26] craftinpark:** Sorry, but then are you sure?

**[01:04:35] david_hong:** is actually still runnable. just the fact that it's gonna break when you form certain action so yes I think it's cues and consumer I think the bug I think that's the thing though like the

**[01:04:49] craftinpark:** Like what if it's like a queues and consumers thing and then the queue gets clogged. It just errors out. I'm just thinking like the, like what are, like, you know, like the, what do you call it? The, the, the case thing, like the upper case, lower case one. That's an example where it's like runnable, but just not working properly. But like, what if the bug like errors you out?

**[01:05:30] david_hong:** bug that the bug that we have to actually test should be a bug that doesn't influence the program at runtime it should for example if it's

**[01:05:43] craftinpark:** Oh, I see.

**[01:05:48] david_hong:** the REST API, right? Then even though the REST API, like certain API is broken, that wouldn't affect the program actually running, but it will affect it when you try to perform a certain action. I think that's the direction that we have to head towards if you're trying to think about the bug.

**[01:06:13] umiclon:** that specific question not runnable wait he actually left oh my god not yet

**[01:06:21] craftinpark:** I see.

**[01:06:27] david_hong:** Ooh, I'm busy on Wednesday. I don't think they have the new Github pre-code let me let me okay I got it

**[01:06:41] chdany12:** This team. I quit this team for being single and useless. Goodbye guys. Okay, so a part of me just wants to create this kind of HTMLs or like some way and then

**[01:06:51] craftinpark:** Bro, would we all get,

**[01:07:06] chdany12:** go run like a solo mode to try to get as much people from as people that you know as much as possible and then come back on Thursday to make like one project. What do you guys think about that? Rather than four of us trying to like talk about something here?

**[01:07:27] craftinpark:** get people to try the Twilio example.

**[01:07:32] chdany12:** Like when I ask these type of questions, I'm going to show my example. So for... Am I still sharing? No, I'm not. Like this one, right? Like this one? Like there's like hints, right? And then like the first version of this was very different, right? So a lot of this changed, and a lot of the hints changed, and the problem itself changed. And the whole point of this was just to make it fun. So I think if a bug is runnable, a bug is not runnable. If it's before running for another bug, we're all going to have different ideas. But I'm saying that whatever the customer's thought was best should always win. And we are not the customers. We can be customers if I make win and all three of you solve it. Or if John makes it, all three of us solve it. We can be. But we should err on the side of bias into the customers the most. So I'm open to ideas. I'm just proving, saying this point. I just think we shouldn't decide on how many questions there are or what type of question it is, or I think it should be runnable because I think we came to the conclusion that everybody wants it to be runnable. Whether it should be runnable for a bug, after a bug, like we can try it, right?

**[01:09:30] craftinpark:** But don't we need something to show, to have them try from start to finish?

**[01:09:36] chdany12:** Yeah, we do.

**[01:09:39] craftinpark:** Will we do four questions for that one? Or just like the multiple choice that we have right now?

**[01:09:47] chdany12:** Yeah, I think, yeah, let's just solve, like, have you solved it, John? Have you solved your own questions?

**[01:09:54] craftinpark:** I did not try this Twilio one.

**[01:09:57] chdany12:** Oh yeah, why don't we just try it? Why don't we just all try it right now?

**[01:10:02] craftinpark:** Okay, let's actually do it.

**[01:10:04] chdany12:** Yeah, let's just do it.

**[01:10:04] craftinpark:** It might be garbage.

**[01:10:05] chdany12:** I feel like, what's stopping us? I feel like we should just do that now. Unless everybody needs to go.

**[01:10:13] craftinpark:** Yeah, I need to push.

**[01:10:15] chdany12:** Anybody needs to go. What's the what branch?

**[01:10:26] craftinpark:** I'll just push the Twilio example right now. Oh, actually I need to push in. Okay, I need to make a push.

**[01:10:52] chdany12:** That's multiple choice questions, so we're gonna be able to solve it pretty fast, right?

**[01:10:58] craftinpark:** Yeah, I hope so. Okay, guys, bear with me, I'm committing. Okay, the branch is called coverage. Hold on, does everybody have the... Yeah, yeah, we made a new repo so that it's not under my name. I'm sending it. I mean, if you guys are not able to pull. Are we having problems?

**[01:13:56] umiclon:** I don't like how minimalistic it is it's not very distracting like other web pages

**[01:14:15] david_hong:** running npm install no 14 minutes I'm gonna meet myself no I'm done like the

**[01:14:19] craftinpark:** Also, this is a huge downgrade in the front end. Maybe for the thing that we're gonna share with our other people will upgrade the front end just. Yeah, it is nice.

**[01:14:43] umiclon:** like I feel I can focus and really lock in still still running npm it's the

**[01:14:45] craftinpark:** That's true, yeah. Yeah. Okay, I'm gonna start it. Oh wait, sorry, not everybody. Danny, do you have it open?

**[01:15:07] chdany12:** Not yet, not yet, I'm struggling.

**[01:15:13] craftinpark:** Okay, I'm gonna start a 30 minute timer when we're all ready.

**[01:15:25] umiclon:** estimated time completion time or like solves solving time yeah it doesn't

**[01:15:34] craftinpark:** Let me check. I don't think this version of the example generator writes that.

**[01:15:56] chdany12:** Yeah, I'm also downloading a NPM, I think.

**[01:16:13] craftinpark:** Bro, API, expect the time of completion for this entire example as 14 minutes. Let's just give ourselves 25 minutes. Should we try 20?

**[01:16:36] chdany12:** Yeah, I'm ready, I'm ready.

**[01:16:38] craftinpark:** OK.

**[01:16:39] umiclon:** matter if we go over under it's kind of slow that's okay I'll I'll use my own

**[01:16:42] craftinpark:** Everyone ready? OK, 3, 2, 1, go. Wait, you're not ready? I started the timer.

**[01:16:54] chdany12:** Too bad, sucks to suck.

**[01:16:57] umiclon:** timer go ahead then 200 is just for anything that passes that's like okay

**[01:35:55] chdany12:** You lads, yo, yo, yo.

**[01:36:10] craftinpark:** David, are you still going? There's 30 seconds. Who wants to go first? Roger, you wanna share?

**[01:36:32] chdany12:** I'll go first, obviously, because I'm the most successful software engineer here. I got two questions right, surprisingly. I got two questions wrong. I think the questions are pretty good. I don't like how I wasn't able to drag this around, like the sidebar. I wish I could expand the sidebar.

**[01:37:08] craftinpark:** Yeah, yeah, that was kind of annoying, to be honest.

**[01:37:14] chdany12:** I think 4 was good in a sense that it forces you to know what rest semantics is. I have no idea what rest semantics is. So I think it's good that I'm failing. I think this is a good signature because it forces you to know what rest semantics is. But it was interesting to see that it fixes the first question. So you could guess what number 1 was wrong by reading 4. So you could kind of game this.

**[01:37:58] craftinpark:** Right, yeah.

**[01:37:59] chdany12:** That was one feedback. And another one is they couldn't control F for 200. I don't know how you guys solved it, but I just searched up the error code and tried to read the code around it by control Fing. But I couldn't find 200, so I don't know if that was just a REST thing, the 200 is okay.

**[01:38:29] umiclon:** If it doesn't return any error, then it's just the 200.

**[01:38:30] chdany12:** But it doesn't have 200 in the code, like is that like a failure or is it supposed to have 200 somewhere?

**[01:38:44] umiclon:** It's like a good default.

**[01:38:47] chdany12:** But I'm saying that the code base doesn't show where it returns 200, it doesn't post 200 anywhere. Okay, so that's, I don't think it's a problem that like 200 doesn't show up in

**[01:38:54] david_hong:** 200 it's like default yeah I think yeah I think that kind of knowledge is

**[01:39:03] chdany12:** the code base, because it's like, we're assuming that it's somewhere outside of this imaginary code base that it actually posts 200 because it's default, right?

**[01:39:12] umiclon:** Yeah, yeah, I can go.

**[01:39:13] chdany12:** Okay.

**[01:39:15] david_hong:** pretty basic I mean sorry like I think like what Roger said like we I think

**[01:39:18] chdany12:** Excuse me. I know. Kidding, kidding. Yeah. Okay. That's it. That's it for me. Do we want it to be multiple choice?

**[01:39:32] craftinpark:** Roger, wanna go next?

**[01:39:34] umiclon:** Yeah, when I opened up the question, I was kind of looking for like a very short intro on the files. Like usually my questions have that, but I also like that it doesn't have it. Like you really have to just go through the Coding Explorer. And I kind of just like looked at the first question and saw that it's like talking about put. So I just went into the code, like tasks, wait, no, where was it? And then just went, found the put, the code, or put, router.put task ID and just like briefly looked over it. and then try to solve the questions. Similarly to, yeah, I got two out of four and then I checked my answers and it was pretty easy to understand what I overlooked. Maybe like, it would be nice to have individual check answer portions. I could check the answer for each question individually or it could just tell me I got two out of four right and I could retry. In terms of the question quality I think it's good it's really good. I was looking at the topics like the rest design, code and error response, request validation, like locking. It seems like all four of the the topics the concepts are covered So if I was looking to solve questions involving this backend, I would be pretty happy with the sample of four questions. That's me. Wait, there's a question one.

**[01:42:18] craftinpark:** Wanna go next?

**[01:42:28] david_hong:** it's good to have like a good like story like a story is really nice it's It's like a good way to first of all simulate real world where we have like a situation going on and it kind of also explains like what this code base is doing. Like at first I was kind of confused on like what it tag was so that is something that I had to look through the code base and stuff like that. I was I was like wondering like what is this task about like like what is this allowed transitions like open like open has an array like in progress has an array like all this stuff it was kind of confusing at first so it took a bit actually to just understand the code um and in terms of like if match like i feel like all right i didn't really like the code base that much in my opinion it was like it's either we need a story or like a description of what we're doing or we need a code base where the things that they do like the naming or whatever like it's better than right yeah okay that makes sense but i feel like like a storytelling

**[01:43:48] craftinpark:** Well, actually, hang on, because I don't know if I'm supposed to be intruding, but the fact that the name was generic makes you actually read it. Okay, yeah, but anyways, continue.

**[01:44:22] david_hong:** would be good in the in the break in the beginning in terms of the code i think it was i think it was pretty good um like it was pretty diverse in a way that you know it would it wouldn't focus on just like one condition but it would do like four two eight four twelve a lot of these stuff but i feel like well this is single file right like there's only one file that actually that's like other other does but like you can kind of tell that you're not going to use that because we're using API routes. I think that was pretty good too like if you really want to dive in deep into testing this person's API test like having one file I think it's still good like we don't have to forcefully like make five or ten files for every single example You know what I mean? So I think that was pretty good here as well. Let's see. Yeah, I feel like the formatting of the question, like when they give you, like this is kind of small, but when they give you the full body of the object, I wish it kind of was in a good structure where you could read it properly because it's like in line, right? So maybe we can make that into like actual JSON structured code. so that could be like a small thing yeah for question one yeah and like what Danny

**[01:46:01] umiclon:** I see. Open-ended, but you can let the user self-grade. Kind of like John's

**[01:46:06] craftinpark:** Yeah, yeah, 100%.

**[01:46:11] david_hong:** said the the back and forth like I want to expand it more yeah overall I think the questions are really good I don't know how but they're pretty good I think I did a good job of that so yeah that's it for me what do you mean

**[01:46:35] chdany12:** I mean, it was good enough, but if we had to make like open end-to-end places for this, like would it, no, not the LLM grader,

**[01:46:45] craftinpark:** I think what's good about the open-ended one, you mean like the LLM grader, right?

**[01:46:51] chdany12:** but I'm talking about like, um, and this is also good, but, uh, like

**[01:47:08] umiclon:** early example, that kind of question. Fixing the blue. I agree. It just kind of like threw me

**[01:47:12] chdany12:** changing the bugs. That one is also a pretty good question to have.

**[01:47:18] craftinpark:** Changing the bug?

**[01:47:20] chdany12:** Like the Quick Eats version, I really like that one too.

**[01:47:20] david_hong:** changing yeah but the problem with that is if you want to make it like that you

**[01:47:21] craftinpark:** Oh, which one?

**[01:47:27] chdany12:** The Quick Eats.

**[01:47:29] craftinpark:** Oh yeah.

**[01:47:31] chdany12:** But I guess it has to be Web UI,

**[01:47:34] david_hong:** have to make the program readable yeah so for example if like this this this

**[01:47:37] chdany12:** it has to be like front end. Okay, well, okay.

**[01:47:46] david_hong:** question right here or this API task resource API question like we can I think we could definitely make something runnable off of this it's just when a certain action happens it'll just not work mm-hmm I think all

**[01:48:04] chdany12:** That's also, that's pretty good. I think one takeaway from this is that this is actually pretty good. So let's get people to do it.

**[01:48:18] craftinpark:** Do we want to like self iterate?

**[01:48:19] chdany12:** And also you wouldn't have to like remember the prompt because remember this is recorded so you can just distill it out of this recording.

**[01:48:22] craftinpark:** Do we want to iterate amongst ourselves any changes before we, you know, send it to the world?

**[01:48:30] david_hong:** things that we talked about like the little here and there. I think the question itself we don't

**[01:48:33] craftinpark:** Oh, like the, the fact that the, the questions, yeah, that's so annoying. Like we collect feedback, I guess.

**[01:48:41] david_hong:** have to change it but it's just like the little um the UI designs here and there. Like you can honestly just ask what to do it and then I feel like after that we should we should try sending this to people. I think this question is actually you can probably easily host it on

**[01:49:07] chdany12:** So I think the next step is for some of you to just push this and I don't know, should we host it somewhere?

**[01:49:16] david_hong:** Yeah, I think collect feedback.

**[01:49:18] chdany12:** Yeah, so I think we can host it and then the rest of us will just try to keep, I guess, playing around with it and then getting people to solve it. What should our next to-do list be?

**[01:49:36] david_hong:** Maybe we could also make it so like you collect feedback and then you can make your own branch off of this one and just pull request and make that change. Like, for example, like, wait, are we trying to get their feedback on the UI or the question quality?

**[01:49:49] craftinpark:** Wait, say that again. I think it's both because the way that the question is presented to the user is also part of the format of the question.

**[01:49:58] david_hong:** Okay, so let's say I asked someone and I got the feedback, then what do I do?

**[01:50:07] craftinpark:** Then we wait and then we reconvene.

**[01:50:08] chdany12:** Yeah, I would ask him, like, would you be sad,

**[01:50:16] david_hong:** I think that's a good idea. I could probably ask a couple of people.

**[01:50:19] craftinpark:** And then we're going to think about how our example type, the TypeScript type needs to change. And then also the UI, how it needs to change. And then thirdly, the prompt for the example generator needs to change. And then we hopefully land on something that we consider, you know, a 70% acceptable. And then we go ham and then we make a coverage for the 500 Golden List. Yeah, for me, this was really good. It actually took me like 12 minutes to do the first question.

**[01:51:11] david_hong:** Okay, so then what should we do for it? When should we meet again? Is it nice?

**[01:51:15] craftinpark:** question and then all the the other questions like started like getting a lot faster but like you know I think there's value in a story but I think it's really good that like um nothing tells you like this is the function and this is what it calls and what it's doing because while I was like honestly for like the first 10 minutes I was like bro like what is this but I had to like piece together my own story and then like I was like like that was like the part of the hunt but then I don't know what the reception on it would be but for me it was enjoyable we can meet I think it wouldn't take a

**[01:52:16] umiclon:** right into there. It really tests your reading comprehension. I can do that.

**[01:52:33] david_hong:** How many feedback do we want? One minimum? Feedback format? Okay.

**[01:52:35] craftinpark:** week to get a feedback right also we we're gonna just get one minimum also be nice if one of us can decide like the feedback format okay yeah just like just the list of questions to like ask the person okay who can who can do the feedback format well we can just

**[01:53:00] david_hong:** Like, you just want us to create a document, or like an actual HTML format?

**[01:53:15] craftinpark:** create a doc and then list the questions i mean we can do it right now right but then i just

**[01:53:19] umiclon:** So, yeah, we can do that.

**[01:53:20] david_hong:** I mean, it can be pretty open-ended, like not open-ended, but flexible.

**[01:53:28] craftinpark:** like what if we're like oh man i should have asked that like because if danny asked a question that I didn't. So, and can somebody help with the Vercell deployment? David, you want to

**[01:53:41] chdany12:** or would you use this in your job prep? If yes, why? If no, why? Another question I would ask is, did you learn something from doing this? Or, to be honest, I also want to give them a runable one, like something that doesn't compile and forces them to read something and fix the bug and sees that, and then tell them that, would you rather this question would you rather the other question or something like that but I don't know how realistic that is and those are the only two questions that I would I would ask to be honest and any other like any other and then a final just like open-ended question of like if you have anything left that you want to say and then they can say something like oh like I I want the things to be able to drag that's all three that I have next Saturday I can't do it this Thursday

**[01:54:50] david_hong:** Or it could be like, oh, does this resemble any of the coding, like, interviews that you've done? This is relevant. But I guess that's question one. okay i i'll try to get two people yeah i'll try it yeah when do you want me to do it by

**[01:55:31] craftinpark:** try doing that? Okay, sorry, I'm just editing the questions. Do you feel that this is relevant?

**[01:55:39] david_hong:** tomorrow i'll try to do it tomorrow morning okay okay i'll try to do that

**[01:55:58] umiclon:** Should we also ask about the concepts, like how relevant it is for them?

**[01:56:04] craftinpark:** I added that right now. Oh, sorry, I'm going to fix the numbering. Well, I think everybody

**[01:56:07] umiclon:** Oh, nice.

**[01:56:28] david_hong:** when are we meeting next saturday saturday

**[01:56:39] chdany12:** What do you propose? Wednesday morning?

**[01:56:43] david_hong:** say 9 p.m. or honestly we could just oh I guess I have to do meet a person I don't know I just feel like next week is too far wouldn't it be faster can we wouldn't we be able to do it faster like get one or two people to just do it and get feedback that we do earlier than Saturday Monday Tuesday oh wait I can't do it Tuesday we could just how about we gather the documents and just upload and maybe John and I could look at them that's true okay I guess I guess just do it next week Saturday at 9 p.m. I feel

**[01:57:34] craftinpark:** needs to be here to help to create the 70% acceptable IAM. Oh, I'll fix the stupid stuff

**[01:57:49] umiclon:** Yep, or we could gather like feedback and like post it and if we have enough feedback, we can maybe make some time.

**[01:58:04] david_hong:** like Saturday is the earliest for every single one of us to be free Wednesday

**[01:58:11] chdany12:** How about like 8.30?

**[01:58:13] david_hong:** morning what time morning I don't think I can do that I have no I have

**[01:58:23] chdany12:** You want me to save you?

**[01:58:27] umiclon:** 8.30 to 9, 9.30?

**[01:58:40] chdany12:** Why not? Day 2? What time?

**[01:58:43] david_hong:** chapel the I have chapel till the day and then on Wednesday I have LTC not LTC but leader leader boy for six hours it's like from like 10 to like like

**[01:58:55] umiclon:** Alright, goodnight guys, good work, goodnight.

**[01:58:56] chdany12:** We can join for the first 30 minutes.

**[01:59:00] david_hong:** four or something I don't know they do go try I'll try I gotta learn the

**[01:59:05] chdany12:** Let's skip leader mode, bro. Okay.

**[01:59:18] david_hong:** chapters okay okay Wednesday Wednesday morning okay I'll try I'll try maybe I Maybe I can do it in my bed. Wednesday, 8.30?

**[01:59:32] chdany12:** Okay. So we all know our to-dos are right?

**[01:59:36] david_hong:** Okay, let's try that. Yeah, and then by tomorrow, I'll try to deploy it.

**[02:00:03] craftinpark:** Like the scroll it having to scroll the questions. I just push it to me. See ya

**[02:00:13] david_hong:** Um, John, you're just gonna do everything on the, what is this branch called? Coverage? Yeah, and then I'll just deploy it on coverage? Okay, okay, okay. I'll deploy the main then. Okay, I'll see you guys.
