Drogulus!
=========

Drogulus is a federated data store and computation platform designed for
simplicity, security, openness and resilience. It's also an exercise in
practical philosophy.

It's heavily based upon ideas from Fluidinfo (an openly writable data store),
Kademlia (a distributed hash table), Lisp, public/private key cryptography with
a dash of Xanadu thrown in for inspiration. It is implemented in Python and
requires very few external dependencies to run.

It'll probably all come to nothing. ;-)

Installation Requirements
+++++++++++++++++++++++++

Drogulus currently only relies upon PyCrypto and zerorpc. Please see these
project's websites for more information:

* https://www.dlitz.net/software/pycrypto/
* https://zerorpc.dotcloud.com/ (you probably need libevent-dev installed).

Alternatively, assuming you have the correct dependencies installed you should
just be able to type::

    $ pip install -r requirements.txt

In any case, you should be able to drop into the Python shell and type the
following without any errors::

    >>> import zerorpc
    >>> import Crypto

What Problems does Drogulus Address?
++++++++++++++++++++++++++++++++++++

The World-Wide Web has become a ghetto of walled gardens built upon years of
technological compromise. Furthermore, the domain name system has become
beholden to the whims of governments and companies without recourse to due
process. Finally, our data is analyzed by companies, sold via targeted
advertising or handed over to governments.

Problem #1: Users are no longer in control of their digital assets.

The relatively simple hypertext system originally envisioned by Tim Berners-Lee
has grown into a monster. It's a plethora of competing technology specified by
committee, built using broken tools to run on quirky browsers that never can
agree on consistency. The resilience of decentralization has been lost as large
parts of the web go dark when certain hosting providers break down.

Problem #2: hackers (used in the positive sense of the word) are obstructed by
incumbent technology from tackling problems with elegant, useful and joyful
solutions.

In order to publish anything most users need third party services to curate
their data on their behalf (enabling problem #1). How this data is organized is
not decided by the user (whose data it is) but by the service provider in such
a way that makes it difficult to change service provider. As if that wasn't
enough, each service requires its own set of credentials making it
hard to tell if the provenance of data on one service is the same as the data
on yet another. Baroque technological solutions have been suggested as a
solution but this is yet another manifestation of problem #2.

Problem #3: At a fundamental level the web isn't openly writable nor does it
make it easy to organize data or link sources of data.

Drogulus is not a Solution
++++++++++++++++++++++++++

Rather, it is a utopian alternative undertaken in the spirit of "what's
the worst that could happen?":

Drogulus is a web of cooperating, decentralized nodes that federate
data in a global key/value store (a distributed hash-table). Users who store
data in Drogulus have no idea of the physical location of the machines holding
their data. Because of this there are no walled gardens.

Every Drogulus node contains a small yet powerful version of a LISP like
programming language used for searching and processing the data stored within
the Drogulus. In fact, in its raw form, data is stored as S-expressions.

Drogulus does not depend on DNS. Under the hood, Drogulus nodes are *only*
referenced by IP address and port number. Data is replicated around Drogulus
should nodes be taken offline by nefarious or accidental reasons so content
remains intact and available.

The identity of users and access to data is based upon public key
cryptography. At the lowest level data is protected by encryption and signing.
Keys in Drogulus's distributed hash-table are partly derived from the public
key of the user whose data is stored there. Data to be stored against a
key is appropriately signed to ensure that nodes can check the provenance of
the key/value being stored.

In a global sense, the user is their public/private key pair.

The network of nodes is ad hoc in nature and can grow / shrink with minimum
risk of data loss.

The implementation details of the distributed nature of Drogulus are hidden
from the end user.

All interactions are asynchronous.

Motivation
++++++++++

Autonomy ~ literally, "autos" (self) "homos" (rule or law) is a favorite word
of mine.

For me, when someone or something is autonomous it is self-directing, free to
act of its own accord and lacking imposition or direct control from external
parties. It also suggests intelligence and awareness enough to be able to enjoy
and make use of such freedom. Furthermore, such intelligence entails ethical and
political considerations on the part of the someone or something. (I'm using the
term "ethics" to mean how an individual makes moral choices and "politics" to
mean how individuals organize themselves within groups).

Autonomy is also the opposite of terms describing such undesirable states as
tyranny, slavery, ignorance and apathy.

My definition contains two different states relating to freedom:

#. Freedom to self-determination, and
#. Freedom from imposition or coercion.

These are Isiah Berlin's famous "Two Concepts of Liberty" (Berlin uses the words
"freedom" and "liberty" interchangeably). He calls them positive and negative
liberty and introduces them by relating them to a question:

    "...the negative sense, is involved in the answer to the question "What is
    the area within which the subject - a person or a group of persons - is or
    should be left to do or be what he is able to do or be, without interference
    by other persons?" The second, ...the positive sense, is involved in the
    answer to the question "What, or who, is the source of control or
    interference that can determine someone to do, or be, this rather than
    that?"

Put simply, negative liberty is freedom from coercion or interference and
positive liberty is freedom to act in a particular way.

Berlin qualifies this by saying that coercion implies deliberate interference
from other persons when one could act otherwise and that the capacity to do or
act in a particular way does not count as a lack of ones political liberty. As
Berlin puts it, "If I say I am unable to jump more than ten feet in the air ...
it would be eccentric to say that I am to that degree enslaved or coerced. You
lack political liberty or freedom only if you are prevented from attaining the
goal by human beings."

Berlin explains, "I wish to be the instrument of my own, not of other men's
acts of will. I wish to be a subject, not an object; to be moved by reasons, by
conscious purposes, which are my own, not by causes which affect me, as it were,
from outside. I wish to be somebody, not nobody; a doer - deciding, not by
external nature or by other men as if I were a thing, or an animal, or a slave
incapable of playing a human role, that is, of conceiving goals and policies of
my own and realizing them."

But are these definitions of freedom/liberty the same as autonomy?

No.

What makes autonomy different is a will to act. Freedom/liberty is a
necessary condition for autonomy but not the only condition. One might have
freedom to do "this" or "that" but, due to habit, laziness, apathy or some other
reason, may simply not do "this" or "that".

In some sense, autonomy requires reflection and then a conscious decision to act
upon one's freedom (positive liberty). However, it's important to acknowledge
this doesn't imply rationality, good behaviour or a good outcome. There are
further considerations beyond autonomy: the ethical and political implications
of exercising autonomy.

So we get to the nub of the essential matter in hand: I believe that autonomy is
a desirable state to aspire to and to encourage. People should have the freedom,
encouragement and means to act autonomously. Furthermore, without such a
freedom to act we are machines devoid of ethical or political responsibility.

What has this got to do with software?

Software is Ethics and Politics
+++++++++++++++++++++++++++++++

So much of our world is (and will be even more) controlled by computers and the
software running on them. Whoever controls the computers controls how things
work which in turn controls what people are able to do and how they are able do
it. This relates directly to the freedoms described above. Unless it is possible
to audit, change and improve the source code of software then we lose both
freedoms: we have no way to become free from the coercion and limitations of
software and we have no way to meld the software to our needs. As Doug Rushkoff
exclaimed, "Program or be Programmed".

This is the same position taken by free software advocates such as the
Free Software Foundation (FSF) (where free is meant in the context of freedom
not gratis).

Yet there are further considerations:

By writing software to be used in such and such a way the designers and
developers are expressing an opinion about how the world should be. Often the
decisions concerning how software should work do not have an ethical or
political dimension yet the end result does insofar as it causes users to
behave and interact in certain ways that cannot be changed by those
participating.

Drogulus is an exercise in personal autonomy. I choose to implement Drogulus in
a way that reflects my emphasis on autonomy with clear philosophical reasons
for certain technological and implementation details.

What is it..?
+++++++++++++

Put simply, Drogulus is a federated, decentralized, openly writable yet
easily searchable information store and distributed computation platform that
includes mechanisms for privacy, provenance and trust via public/private key
technology.

Being federated (the system consists of many independent but collaborating
entities) and decentralized (no entity is more important than any of the others)
ensures users are free from a central authority that might desire to control
their use of the system. This is a decision that reflects Berlin's concept of
negative liberty.

Being openly writable ensures no user is barred from the system. All users are
free to contribute, change, enhance and expand the system. This reflects
Berlin's concept of positive liberty.

Being easily searchable enables users to explore the information stored via
Drogulus without having to rely on others to provide such services. This
reflects both positive and negative concepts of liberty: the freedom to search
whilst being free from a broker for such searches (the facility is built in).

Being a distributed computation platform enables users to do something useful
with the information they find via Drogulus. By distributed computation I mean
running programs on the shared resources that Drogulus provides. This
facilitates acting on information obtained via Drogulus in order to exercise
autonomy.

Having a mechanism for privacy, provenance and trust makes it possible to save
information via Drogulus without fear of having it made public, ensures you know
the source of any information obtained via Drogulus and allows you to share
your information with only those that you trust. It ensures users of Drogulus
know who each other are and retain control of their information without needing
to rely on external parties.

Etymology of Drogulus
+++++++++++++++++++++

I've always thought that "Drogulus" is a catchy name for a project. I first
heard of the term whilst driving through the Lake District in the early hours of
the morning during a trip on my honeymoon in 1997. BBC Radio 4 was
re-broadcasting the debate I mention below.

Here's the story of its origin:

A drogulus is an entity whose presence is unverifiable, because it has no
physical effects.

The atheist philosopher A.J. Ayer coined it as a way of ridiculing the belief
system of Jesuit philosopher Frederick Copleston.

In 1949 Ayer and Copleston took part in a radio debate about the existence of
God. The debate then went back and forth, until Ayer came up with the following
as a way of illustrating the point that Copleston's metaphysics had no content
because there was no way of testing the truth of metaphysical assertions. He
said:

    "I say, 'There's a "drogulus" over there,' and you say, 'What?' and I say,
    'drogulus' and you say 'What's a drogulus?' Well, I say, 'I can't describe
    what a drogulus is, because it's not the sort of thing you can see or
    touch, it has no physical effects of any kind, but it's a disembodied
    being.' And you say, 'Well how am I to tell if it's there or it's not
    there?' and I say, 'There's no way of telling. Everything's just the same
    if it's there or it's not there. But the fact is it's there. There's a
    drogulus there standing just behind you, spiritually behind you.' Does that
    makes sense?"

Of course, the natural answer Ayer was waiting for was "No, of course it
doesn't make sense." Therefore, the implication would be that metaphysics is
like the "drogulus" ~ a being which cannot be seen and has no perceptible
effects. If Ayer can get to that point, he can claim that any kind of belief
in the Christian God or in metaphysical principles in general is really
contrary to our logical and scientific understanding of the world.

This appealed greatly to our sense of humour and we ended up talking about the
debate for most of the rest of our journey.

Happy days..! :-)
