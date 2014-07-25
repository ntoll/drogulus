Contributing to the drogulus
----------------------------

Hey! Many thanks for wanting to improve the drogulus.

Contributions are welcome without prejudice from *anyone* irrespective of
age, gender, religion, race or sexuality. Good quality code and engagement
with respect, humour and intelligence wins every time.

Feedback may be given for contributions and, where necessary, changes will
be politely requested and discussed with the originating author. Respectful
yet robust argument is most welcome.

Legal Status
++++++++++++

The drogulus is released into the public domain. Please read the UNLICENSE
file for the legalese about this.

In the interests of keeping things simple, any contribution to the source code
(including documentation) will be subject to the following conditions:

* The contribution was created by the contributor who confirms they have the
  authority to place their contribution in the public domain (see instructions
  below for how to do this).

* Since all development of the drogulus is done in public, the contribution
  will be made public.

* There is no guarantee that a proposed contribution will be accepted in to
  the source code.

Contributors should accompany their work with the following simple statement
(for example as part of a commit message)::

    I dedicate any and all copyright interest in this software to the
    public domain. I make this dedication for the benefit of the public at
    large and to the detriment of my heirs and successors. I intend this
    dedication to be an overt act of relinquishment in perpetuity of all
    present and future rights to this software under copyright law.

Alternatively, major contributors should digitally sign the WAIVER file and
add the resulting signature to the AUTHORS file. Use the following command to
do this using GnuPG::

    $ gpg --no-version --armor --sign WAIVER

If the above process is insufficient for whatever reason, please feel free to
get in touch.

Code Contribution Checklist
+++++++++++++++++++++++++++

* If you're submitting code, include tests!

* Your code should be commented in *plain English*.

* Ensure you run ``make check`` to tell you that you're following PEP8,
  PyFlakes isn't complaining about redundant code, all the tests pass and you
  have as close to 100% test coverage as is possible.

* If you're submitting documentation make sure you run ``make docs`` and that
  you see your contribution as expected.

* If your contribution is for a major block of work and you've not done so
  already, add yourself to the AUTHORS file in the manner outlined at the end
  of the "Legal Status" section above.
