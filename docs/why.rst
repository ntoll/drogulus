Why is there a Drogulus?
++++++++++++++++++++++++

The Internet is a Mess
======================

The World-Wide Web has become a ghetto of walled gardens built upon years of
technological compromise. DNS (used to link domain names with their host
computer) is beholden to the whims of governments and companies without
recourse to due process. More worryingly still, our data is analyzed by
companies, sold via targeted advertising or handed over to governments without
our consent.

Problem #1: Users are no longer in control of their digital assets.

In order to publish anything on the web most users need third party services
(web sites) to curate data on their behalf. How this data is organized is
usually not decided by the user whose data it is but by the service provider.
Furthermore, how this data is stored and made available is often done in such a
way that makes it difficult to change service provider. As if that wasn't
enough, each service requires its own set of credentials to identify the user -
making it hard to tell if the provenance of data on one service is the same as
data on yet another. Baroque technological solutions have been proposed to
solve the problem of multiple identities on different services but these are
merely a manifestation of problem #2 (see below).

Problem #2: hackers (used in the positive sense of the word) are obstructed by
incumbent technology from tackling problems with elegant, useful and joyful
solutions.

The beautifuly simple hypertext system originally envisioned by Tim Berners-Lee
has grown into a monster. It's a plethora of complex technologies specified by
committee that run on quirky browsers which never behave consistently. The
ubiquity of the web also means it has assumed the status of de-facto platform
for solutions thoughtlessly implemented in a sub-optimal way in order to cope
with the limitations of web based technology. Furthermore, the resilience of the
web's decentralized nature has been undermined: large parts of the web go dark
when certain hosting providers break down or if popular websites fall over.

Problem #3: At a fundamental level the web isn't openly writable or
configurable.

Creating, editing or organising content is not part of the web itself, but
implemented at a higher level of abstraction (causing problem #1) in a way that
abuses and complicates the original simple hypertext system (see problem #2).
This technical situation has profound political and ethical implications
concerning control, privacy and participation. Such potential disempowerment
extends to DNS - a single point of control over linking domains to computers.
As a result, naming places on the Internet requires permission and a single
use name.

Drogulus is not a Solution
==========================

Rather, it is a utopian alternative undertaken in the spirit of asking "what's
the worst that could happen?":

Drogulus is a web of cooperating, decentralized nodes that federate
data in a global key/value store (a distributed hash-table). Users who store
data in Drogulus have no idea of the physical location of the machines holding
their data. Because of this there are no walled gardens, there is only the
Drogulus.

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

In a global sense, the user is their public/private key pair and is the only
form of identity they need.

The network of nodes is ad hoc in nature and can grow / shrink with minimum
risk of data loss.

The implementation details of the distributed nature of Drogulus are hidden
from the end user.

All interactions are asynchronous.

Motivation
==========

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
encouragement and means to act autonomously. Furthermore, without such freedom
to act we are machines devoid of ethical or political responsibility.

What has this got to do with software?

Software is Ethics and Politics
===============================

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

