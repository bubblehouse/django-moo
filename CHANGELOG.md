## [0.94.7](https://gitlab.com/bubblehouse/django-moo/compare/v0.94.6...v0.94.7) (2026-04-09)

### Bug Fixes

* dont send messages to queues of disconnected players ([df9f798](https://gitlab.com/bubblehouse/django-moo/commit/df9f798e490a91bef808aea9838661fed601242a))
* dont send messages to queues of disconnected players ([aa11140](https://gitlab.com/bubblehouse/django-moo/commit/aa1114086e005326baa1e9dab86689ba5c068a9a))
* handle ssh reconnection and other agent issues ([d65efe6](https://gitlab.com/bubblehouse/django-moo/commit/d65efe63b823a05173f015723b6751178fe4f627))
* verbs and properties should be owned by the player creating them ([7a702e4](https://gitlab.com/bubblehouse/django-moo/commit/7a702e46033665b32ef702375b8f7b1ddf41cbf8))

## [0.94.6](https://gitlab.com/bubblehouse/django-moo/compare/v0.94.5...v0.94.6) (2026-04-08)

### Bug Fixes

* more agent tuning ([51eb085](https://gitlab.com/bubblehouse/django-moo/commit/51eb0859e0be0f04f858e3f419f5d0d08a25f0e0))

## [0.94.5](https://gitlab.com/bubblehouse/django-moo/compare/v0.94.4...v0.94.5) (2026-04-08)

### Bug Fixes

* more agent tuning ([e89a4bf](https://gitlab.com/bubblehouse/django-moo/commit/e89a4bfac8ee83d50a30f0c788e866645b868a0d))

## [0.94.4](https://gitlab.com/bubblehouse/django-moo/compare/v0.94.3...v0.94.4) (2026-04-08)

### Bug Fixes

* added stocker agent for consumables, other agent updates ([d15f74b](https://gitlab.com/bubblehouse/django-moo/commit/d15f74b6e998e24416a41267cabbb4bc9968af2b))

## [0.94.3](https://gitlab.com/bubblehouse/django-moo/compare/v0.94.2...v0.94.3) (2026-04-08)

### Bug Fixes

* more agent training ([61b6dce](https://gitlab.com/bubblehouse/django-moo/commit/61b6dce76672e7a82b1b462076dd0ed0a03d4a89))

## [0.94.2](https://gitlab.com/bubblehouse/django-moo/compare/v0.94.1...v0.94.2) (2026-04-08)

### Bug Fixes

* cover more bizarre [@create](https://gitlab.com/create) scenarios ([d21096a](https://gitlab.com/bubblehouse/django-moo/commit/d21096adbd99ba01dc5d023161abdc6358660041))
* dont send messages to queues of disconnected players ([16f3e96](https://gitlab.com/bubblehouse/django-moo/commit/16f3e964ae2290c80d143697c8c6d2a830ae037e))
* improve security around task permission escalation ([f458570](https://gitlab.com/bubblehouse/django-moo/commit/f458570efc41073ca2f45e775027e85615d2ddc2))
* improved agent token handling, test updates ([ae0d2e8](https://gitlab.com/bubblehouse/django-moo/commit/ae0d2e8c4d6dff6fdb48506ca4b0d2085495e04d))
* refactored agent baseline knowledge, created new unused stocker agent ([150416f](https://gitlab.com/bubblehouse/django-moo/commit/150416fc3a780742bb714b4aee66456bc07d5fdb))
* transaction handling in object.save() ([8e00686](https://gitlab.com/bubblehouse/django-moo/commit/8e006866b1311aecdd91d30b9fb1c2f7e9c6fc48))

## [0.94.1](https://gitlab.com/bubblehouse/django-moo/compare/v0.94.0...v0.94.1) (2026-04-07)

### Bug Fixes

* several issues contributing to SSH server hang ([7c48a77](https://gitlab.com/bubblehouse/django-moo/commit/7c48a77fccc0207c3c86a8f0e310dfa5a22320e7))

## [0.94.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.93.2...v0.94.0) (2026-04-07)

### Features

* add a foreman agent to coordinate the rest ([26b9331](https://gitlab.com/bubblehouse/django-moo/commit/26b9331af08b3eddd9f125b450e4ce554ba79078))

### Bug Fixes

* handle failed teleportation ([17c6c0e](https://gitlab.com/bubblehouse/django-moo/commit/17c6c0e93cea46e7b870863d25be81ba1cafa387))
* post-run agent updates ([dba7bdf](https://gitlab.com/bubblehouse/django-moo/commit/dba7bdf6994e1351aaf03816ea9986d548e607f9))

## [0.93.2](https://gitlab.com/bubblehouse/django-moo/compare/v0.93.1...v0.93.2) (2026-04-07)

### Bug Fixes

* dont use moveto with [@create](https://gitlab.com/create) ([7642f95](https://gitlab.com/bubblehouse/django-moo/commit/7642f9590fe1293911177f6361df1b326c7fc53c))
* use correct dpec for [@edit](https://gitlab.com/edit) on $note ([84c3b73](https://gitlab.com/bubblehouse/django-moo/commit/84c3b73302c98f30d301746f26296d2f3d3d5f98))

## [0.93.1](https://gitlab.com/bubblehouse/django-moo/compare/v0.93.0...v0.93.1) (2026-04-06)

### Bug Fixes

* mypy typing errors ([ab68605](https://gitlab.com/bubblehouse/django-moo/commit/ab68605fdfe3cb8ca9ead617fe97fe7ff8bfac01))

## [0.93.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.92.0...v0.93.0) (2026-04-06)

### Features

* add [@create](https://gitlab.com/create)...in support ([73b32e2](https://gitlab.com/bubblehouse/django-moo/commit/73b32e2f3efc4c63936c9c8ecfd56d9a3f9f30d3))
* add $nothing sentinel objects and stale-ref replacement ([c5106ce](https://gitlab.com/bubblehouse/django-moo/commit/c5106ceea58cc847f87402819b7c43816c806150))
* add agent-optimized navigation and inspection verbs ([7d00f82](https://gitlab.com/bubblehouse/django-moo/commit/7d00f82af17af336367f2420c7ac926dc476bca1))
* added [@add](https://gitlab.com/add)_parent and [@remove](https://gitlab.com/remove)_parent verbs ([f894b26](https://gitlab.com/bubblehouse/django-moo/commit/f894b26b5af88c4073fd5666599df702e7aa1d83))
* added [@add](https://gitlab.com/add)_parent and [@remove](https://gitlab.com/remove)_parent verbs ([0c25994](https://gitlab.com/bubblehouse/django-moo/commit/0c25994e7986feb40deda4db440ea8bbd2bb4b23))
* configure tradesmen agents into iterative loop ([2852275](https://gitlab.com/bubblehouse/django-moo/commit/285227511d58c1cfc19a83755b1226c37cb44f4c))
* expose new navigation verbs as agent tool specs ([0ab4b54](https://gitlab.com/bubblehouse/django-moo/commit/0ab4b545cc0c6f657007c38d030211a9dbd7994e))

### Bug Fixes

* derive to everyone on all standard system classes ([991a841](https://gitlab.com/bubblehouse/django-moo/commit/991a841b91bbc3b283bd38067a236d6780d8e104))
* enterfunc/exitfunc json decode issue ([cdbdbfd](https://gitlab.com/bubblehouse/django-moo/commit/cdbdbfd1d3bd5af3c5ac7f7a5d571ecc07982976))
* improved verb handling ([cdcd1c8](https://gitlab.com/bubblehouse/django-moo/commit/cdcd1c8dfd46c1aa96b0e4771295e2a118e61cd3))
* move import lookup ([9700334](https://gitlab.com/bubblehouse/django-moo/commit/9700334aa12c6dfdac5f8a00b4846762071954e4))
* page should use a global lookup ([ff49ab0](https://gitlab.com/bubblehouse/django-moo/commit/ff49ab024219ea4e7e50d4852e27ccddb6c1324f))
* remove spurious LF in print() output ([4e5f4ed](https://gitlab.com/bubblehouse/django-moo/commit/4e5f4ede4383c2bbe8c53d4f844016d8b1df36e9))
* the transaction needs to be inside the contextmanager, not vice-versa ([ca69346](https://gitlab.com/bubblehouse/django-moo/commit/ca69346d78e96b0474033a6aa28d31e19900f3d6))

## [0.92.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.91.1...v0.92.0) (2026-04-06)

### Features

* added tool use support to moo-agent ([df4ff8d](https://gitlab.com/bubblehouse/django-moo/commit/df4ff8d1013ee4ecb6577a77741ed0bf509e1f04))
* split builder agent into mutiple simpler agents ([c8b5862](https://gitlab.com/bubblehouse/django-moo/commit/c8b5862cf8f26f10f7790f1f3fe8397a3a5e84c1))

### Bug Fixes

* [@create](https://gitlab.com/create) should use the current player as the owner ([d68b769](https://gitlab.com/bubblehouse/django-moo/commit/d68b769e4375f2eb2ae2fbd245d8b651ee55774d))
* [@edit](https://gitlab.com/edit) improvements for stupid agents ([c2f77d2](https://gitlab.com/bubblehouse/django-moo/commit/c2f77d21084d78a37ca719eb0b0a8d4e87be5cfa))
* add synonyms for dspec and ispec ([294a2f1](https://gitlab.com/bubblehouse/django-moo/commit/294a2f15a638481049f9979b2934c1d2c0179d47))
* agent updates to self-train after mistakes ([ed9ec6a](https://gitlab.com/bubblehouse/django-moo/commit/ed9ec6a23c187bb96b7b0896f49fc246e4c7832c))
* argument handling for [@move](https://gitlab.com/move) ([973bd89](https://gitlab.com/bubblehouse/django-moo/commit/973bd89020bd492c55b6c3c81e41b474ca3a3c92))
* edit edge case behavior ([0cbce0e](https://gitlab.com/bubblehouse/django-moo/commit/0cbce0e18590314857451a3b4b374053c62989ae))
* edit test fixes ([62ec327](https://gitlab.com/bubblehouse/django-moo/commit/62ec3279b73c3078878316837b0c73ea9a4238ba))
* error handling for bad shebang ([498667b](https://gitlab.com/bubblehouse/django-moo/commit/498667bd9df10947171f2326681a7b60e98e9b6e))
* import error ([820211e](https://gitlab.com/bubblehouse/django-moo/commit/820211e374a18ff4624858d9776daf7e32c7a138))
* improve agent permission and multiuser performance ([669c787](https://gitlab.com/bubblehouse/django-moo/commit/669c787733c9e3043cdec3f6aad8b659d0df96f8))
* improve quote handling ([1f4f600](https://gitlab.com/bubblehouse/django-moo/commit/1f4f6002ce7985636ebca522f66a4ab8af8430bd))
* moveto improvements ([eda4603](https://gitlab.com/bubblehouse/django-moo/commit/eda4603a09b43df374f40713125362ad01f448ae))
* put agent users in the void so tests dont fail ([57fa09d](https://gitlab.com/bubblehouse/django-moo/commit/57fa09d5580f001f49128fa10adc19e46ae0a0c2))
* raise permissionerror to user ([0cbccaf](https://gitlab.com/bubblehouse/django-moo/commit/0cbccaff61d1cdb77e58708aec75968ca744f143))
* say routing fixes ([7546cd9](https://gitlab.com/bubblehouse/django-moo/commit/7546cd96af3fd46a865dffb96b89e6ed8e217371))
* try to translate bare tool-call syntax before sending as MOO command ([6284d7e](https://gitlab.com/bubblehouse/django-moo/commit/6284d7ef736dfa734b1ed12af002942fdaaf1733))

## [0.91.1](https://gitlab.com/bubblehouse/django-moo/compare/v0.91.0...v0.91.1) (2026-03-31)

### Bug Fixes

* added with support to [@edit](https://gitlab.com/edit) on $note ([8a7cd5f](https://gitlab.com/bubblehouse/django-moo/commit/8a7cd5f2516a6a68726ea21ccd12198d71dd7bee))
* agent stall on non-response ([e596407](https://gitlab.com/bubblehouse/django-moo/commit/e5964071ff9119d796658d8d5ed2665708e6da40))
* brain updates for gemma ([d0ecab3](https://gitlab.com/bubblehouse/django-moo/commit/d0ecab3e0fef96512d0a2efaf7947bc3376c241b))
* parser bug when using here in certain scenarios ([e7477e3](https://gitlab.com/bubblehouse/django-moo/commit/e7477e370e3b770bf78603c5e62958ea1fee3b3e))

## [0.91.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.90.1...v0.91.0) (2026-03-30)

### Features

* added agent support for local inference....one day ([a106b8c](https://gitlab.com/bubblehouse/django-moo/commit/a106b8c9331f70800f634d01a3e1d8545377090a))
* support Bedrock in moo-agent ([1f78557](https://gitlab.com/bubblehouse/django-moo/commit/1f78557f65bdd3ee87613cbd1398bd5775ed5101))

### Bug Fixes

* added response to [@move](https://gitlab.com/move) ([f92ce4c](https://gitlab.com/bubblehouse/django-moo/commit/f92ce4c0f9df0b7a28d3b7bdbbf97f8f10dffd5a))
* after a script, print a summary of what you did ([0438162](https://gitlab.com/bubblehouse/django-moo/commit/04381628bdba8e444ebf7a41b508db6dcdef2905))
* agent should pre-generate a list of commands rather than doing each one by one ([78891a1](https://gitlab.com/bubblehouse/django-moo/commit/78891a1a8e6a0f825f73a4c2c5c76bcc68d7a931))
* create unique message queue names ([7ea6613](https://gitlab.com/bubblehouse/django-moo/commit/7ea66139fe7f580adeb7ccb4c3750e3fa0d04f74))
* dont silently discard extra markdown blocks ([bdf1c78](https://gitlab.com/bubblehouse/django-moo/commit/bdf1c7814174e86112c0bf96ab566a8fe0851dfa))
* eagerly flush the buffer so content doesnt get lost by the agent ([76f8ae2](https://gitlab.com/bubblehouse/django-moo/commit/76f8ae270ddd733cb28d13c6c92311ddfbbe443a))
* encourage agent to pre-generate a script of commands it needs to run ([b40d08e](https://gitlab.com/bubblehouse/django-moo/commit/b40d08e387304b5f5905d0e5f932dc6389b0822f))
* ignore connection settings leftover from previous connections ([fc60821](https://gitlab.com/bubblehouse/django-moo/commit/fc6082150a14d542f49116fb7cd7f5ae2f5a227e))
* improve agent context and resume behavior ([2e51e36](https://gitlab.com/bubblehouse/django-moo/commit/2e51e364aa34cc898f52258b53d247e443839e39))
* more agent edge cases ([0122372](https://gitlab.com/bubblehouse/django-moo/commit/012237206d92cb652244b4320c6225dba5be2f98))
* more agent edge cases ([174e903](https://gitlab.com/bubblehouse/django-moo/commit/174e9033a354e72a038b044d600d91e1e9031bf7))
* more script handling issues ([5612634](https://gitlab.com/bubblehouse/django-moo/commit/5612634a9c45e04e009ab6946a664571d1c5d470))
* properly reload verbs with asterisks ([ef85af9](https://gitlab.com/bubblehouse/django-moo/commit/ef85af903388bbf184def37ed246d5afbadeaa8c))
* shell and [@edit](https://gitlab.com/edit) edge-case handling, agent fixes ([3af9108](https://gitlab.com/bubblehouse/django-moo/commit/3af9108ea678aeef3c4e741801eafb19854cded2))
* style update ([529a590](https://gitlab.com/bubblehouse/django-moo/commit/529a5903d0b45d8b0ee0d7db0d815ab3ec6fca7e))
* timing and race issues in shell ([71e29c8](https://gitlab.com/bubblehouse/django-moo/commit/71e29c8889bb3e2c3ade653fe0808c674977d839))
* use bedrock by default, other startup fixes ([309eef6](https://gitlab.com/bubblehouse/django-moo/commit/309eef6c5089412c2100d5f2b13f29e4a9a2c9d0))

## [0.90.1](https://gitlab.com/bubblehouse/django-moo/compare/v0.90.0...v0.90.1) (2026-03-29)

### Bug Fixes

* dont display output separators ([89aff7e](https://gitlab.com/bubblehouse/django-moo/commit/89aff7e5d09e2a9b227bca335a1d74d5e247d2e3))
* edge case when db is reset but redis is not ([e211a46](https://gitlab.com/bubblehouse/django-moo/commit/e211a4686b3df4448c54aef3c036d0ee9a3acc89))
* futher agent bugs ([32805f4](https://gitlab.com/bubblehouse/django-moo/commit/32805f413118faf1257535c3b8c54b4d5d2aec5f))
* improve agent text handling ([739087d](https://gitlab.com/bubblehouse/django-moo/commit/739087de947a0182dc06f197e6c1bf009407a9c6))
* more agent edge cases ([12728f3](https://gitlab.com/bubblehouse/django-moo/commit/12728f34185bdb1ecb8789f5f7d987a7ea90502e))

## [0.90.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.89.3...v0.90.0) (2026-03-29)

### Features

* implemented moo-agent for autonomous experiments ([76c2b1b](https://gitlab.com/bubblehouse/django-moo/commit/76c2b1b8324d0cba3644d82b8b96e29300d9b38f))

### Bug Fixes

* more scroll handling, other agent fixes ([4fc5770](https://gitlab.com/bubblehouse/django-moo/commit/4fc57709e9b78feb1a9f49c3de1926c12d408ff7))
* scroll handling in agent TUI ([16bf6ac](https://gitlab.com/bubblehouse/django-moo/commit/16bf6ac84fa124b5cf251919242c6779adde6c4c))

## [0.89.3](https://gitlab.com/bubblehouse/django-moo/compare/v0.89.2...v0.89.3) (2026-03-28)

### Bug Fixes

* ignore errors when calculating coverage ([c0fe3da](https://gitlab.com/bubblehouse/django-moo/commit/c0fe3da6687d47c3b3a20ed7a5502d51aeea5705))

## 1.0.0 (2026-03-28)

### Features

* add a celery runner to docker-compose ([b8ac932](https://gitlab.com/bubblehouse/django-moo/commit/b8ac932c335a2646c4bbaa1f828e9181a82bed7f))
* add celery with django and redis integration ([3a3a460](https://gitlab.com/bubblehouse/django-moo/commit/3a3a460b5c8974ec117470ca2d34b12d91a86e51))
* add devcontainer support ([ba8214d](https://gitlab.com/bubblehouse/django-moo/commit/ba8214d2f8c03f325871212d8f91315010ae8865))
* add inherited field to property ([6a51bf2](https://gitlab.com/bubblehouse/django-moo/commit/6a51bf2e59cf5a37fd05e8a2ddbda5f58e32187e))
* add intrinsic `obvious` property to improve object searching ([91be1d4](https://gitlab.com/bubblehouse/django-moo/commit/91be1d4925571fefe265aa99c466025348f1b5dd))
* add missing LambdaCore verbs and functions ([d844518](https://gitlab.com/bubblehouse/django-moo/commit/d8445185f4a97b98619f4ab725484b863f2119fa))
* add object.invoke_verb() ([bce1e76](https://gitlab.com/bubblehouse/django-moo/commit/bce1e76f8bb813822072ca2ba1f8fb07f888d41d))
* add redis as a chart dependency ([bb01577](https://gitlab.com/bubblehouse/django-moo/commit/bb0157794ac44a8897ad1a60713a58355bf843a6))
* add shell to compose file ([8f22cb0](https://gitlab.com/bubblehouse/django-moo/commit/8f22cb08ad97eae3526866a3334d3c685a0163ab))
* add simple text editor feature that can be used by wizard verbs ([e94134b](https://gitlab.com/bubblehouse/django-moo/commit/e94134b24b5383501d8ff4d440831f793b6852f9))
* add support for asterisk wildcard when creating verbs, closes [#8](https://gitlab.com/bubblehouse/django-moo/issues/8) ([997be84](https://gitlab.com/bubblehouse/django-moo/commit/997be84b7a75d68a4d95f70b16262558327036d9))
* add support for SSH key login ([c673266](https://gitlab.com/bubblehouse/django-moo/commit/c673266e1707d513bdc00c49926e6102a73675cf))
* add webssh deployment to helm chart ([d61b6fd](https://gitlab.com/bubblehouse/django-moo/commit/d61b6fd50a4f90d3f0b3e80b2f464096be31dae2))
* added ; shortcut for [@eval](https://gitlab.com/eval) ([1b9ca01](https://gitlab.com/bubblehouse/django-moo/commit/1b9ca01644658866ff9512c1538846b81b3a727c))
* added "either" dspec to support verbs with optional direct objects ([8e17581](https://gitlab.com/bubblehouse/django-moo/commit/8e17581e6c2dc6aefe8821b51182f3b9add829c6))
* added [@alias](https://gitlab.com/alias) function for all players ([6134c14](https://gitlab.com/bubblehouse/django-moo/commit/6134c14eb80a01fbe8e19915044de32e6268af50))
* added [@edit](https://gitlab.com/edit) verb to default_verbs ([5d3a144](https://gitlab.com/bubblehouse/django-moo/commit/5d3a144de74833df89c08716bb2f7ae29106a4db))
* added [@eval](https://gitlab.com/eval) verb for $programmers ([476806a](https://gitlab.com/bubblehouse/django-moo/commit/476806afe009d7b330b4103f73c4710cfcb2d51f))
* added [@reload](https://gitlab.com/reload) verb to update filesystem-resident verbs in the database ([a3a2eb3](https://gitlab.com/bubblehouse/django-moo/commit/a3a2eb39378e278c6a734dffe6d7787002d197b2))
* added `random` to sandbox imports ([448e4b2](https://gitlab.com/bubblehouse/django-moo/commit/448e4b21d69aaafa0d874d3862a17759120ca827))
* added $do_command support, closes [#7](https://gitlab.com/bubblehouse/django-moo/issues/7) ([725e205](https://gitlab.com/bubblehouse/django-moo/commit/725e20527eab62b2e20e2a63d9bdea6ed61e8f55))
* added $furniture class for immovable sittable objects ([e88a1b0](https://gitlab.com/bubblehouse/django-moo/commit/e88a1b04f9ebc682b2c5e9da1368e2231cae3972))
* added $gender_utils and tests ([1eeaed3](https://gitlab.com/bubblehouse/django-moo/commit/1eeaed3374205796e7bdb286d5f9f84c8424ba82))
* added $note and $letter classes ([9a107ac](https://gitlab.com/bubblehouse/django-moo/commit/9a107aca2a04e96c7ce6807855f857ef596eac24))
* added $sprintf alias for easy access to the `pronoun_sub` verb ([26a2544](https://gitlab.com/bubblehouse/django-moo/commit/26a2544eac89b7093c4cde88464e8ef9f73d3230))
* added $string_utils and tests ([d3e3fb6](https://gitlab.com/bubblehouse/django-moo/commit/d3e3fb6b85c213ee384f853edf85a454aed3e091))
* added add_ancestor with inheritence of properties ([24223cb](https://gitlab.com/bubblehouse/django-moo/commit/24223cbccdcf0f3280d758e17e2f1373a0152d7a))
* added additional syntaxes to [@reload](https://gitlab.com/reload) ([e3bf2e0](https://gitlab.com/bubblehouse/django-moo/commit/e3bf2e0a5bcbba6adb66d3e781fd1328c09c036c))
* added alternate prompt mode for MUD mode ([a1cc3b5](https://gitlab.com/bubblehouse/django-moo/commit/a1cc3b50c953d215a1fb4d815f804bc6ee08109d))
* added API descriptor value for the Celery task_id ([205ec08](https://gitlab.com/bubblehouse/django-moo/commit/205ec0841ccbf91a184bc5903f3ce054f9854424))
* added boot_player() and implemented true [@quit](https://gitlab.com/quit) verb ([1ffa492](https://gitlab.com/bubblehouse/django-moo/commit/1ffa49289308ddd89adf0e784ead333ed447529b))
* added contents to look output ([5333085](https://gitlab.com/bubblehouse/django-moo/commit/533308541491b79dd7850bb15319d6c1a0fe82f8))
* added context.task_time object to help write verbs that last longer than the timeout ([14e1078](https://gitlab.com/bubblehouse/django-moo/commit/14e1078e13c4119e4e48e6602e192262a423b4cb))
* added has_property ([f8946af](https://gitlab.com/bubblehouse/django-moo/commit/f8946af41ae9a44530c224865e9d14e12e82ec23))
* added improved handling of multple prepositions ([1959259](https://gitlab.com/bubblehouse/django-moo/commit/19592594e641ae0bf11b2b2664fed5c87c5c01ef))
* added key support and parsing, modify tests to use variable PKs ([16f1a52](https://gitlab.com/bubblehouse/django-moo/commit/16f1a52c7c71ffdb95211f2cf2727986e798cd84))
* added last_connection_time property, connected_users() helper function, and use it in look_self on the player object ([92a551e](https://gitlab.com/bubblehouse/django-moo/commit/92a551ec58e33eb6fd25567496440659c10e975b))
* added lookup boolean to parser methods ([bdf286c](https://gitlab.com/bubblehouse/django-moo/commit/bdf286c57d63ed4cb1c6e7a92b3d1b3e71823a59))
* added many verbs for $player ([bcf2fd9](https://gitlab.com/bubblehouse/django-moo/commit/bcf2fd9e5d8ea9b68ae5256a19e3b9ef4ac98d08))
* added moo_enableuser command ([682a637](https://gitlab.com/bubblehouse/django-moo/commit/682a637b773c82b57c9f4c1c4b64929a89a14c02))
* added more invocation styles for [@edit](https://gitlab.com/edit) ([95b2dfa](https://gitlab.com/bubblehouse/django-moo/commit/95b2dfa44ace935f1af0f27c0fed4d919637dd3f))
* added more verbs for $player ([23c7e30](https://gitlab.com/bubblehouse/django-moo/commit/23c7e307b809672f84598e08993e5b1990dea314))
* added more verbs for $player ([d720a67](https://gitlab.com/bubblehouse/django-moo/commit/d720a67b62645d4e78f0b7175069bee8ca71bcaa))
* added more verbs for $player ([cca497d](https://gitlab.com/bubblehouse/django-moo/commit/cca497d26eb9e149c515a00dc2fdb85b13c6cf17))
* added object quotas and initialization ([3756777](https://gitlab.com/bubblehouse/django-moo/commit/375677797ccea7fb43c0b3a7c39b7339857cc263))
* added open_paginator client function ([3fb107e](https://gitlab.com/bubblehouse/django-moo/commit/3fb107ec6a259e325a249ad9c558dedf131673e2))
* added paginator support to [@show](https://gitlab.com/show) to show verbs and properties ([c1387c3](https://gitlab.com/bubblehouse/django-moo/commit/c1387c39d40d85c2cc8dd03aad49253dbec25687))
* added parser/lexer, very early successes with each ([cba8f27](https://gitlab.com/bubblehouse/django-moo/commit/cba8f2724292ae2f0d42c9447f2c963676cdb27c))
* added PREFIX/SUFFIX/QUIET verbs to manage client connection features ([91785ac](https://gitlab.com/bubblehouse/django-moo/commit/91785ac39ac32c0294503d26451f058184e3b809))
* added preliminary door support ([d71bd75](https://gitlab.com/bubblehouse/django-moo/commit/d71bd75138d93e9a5dbd9d1e0627f9a29e2f1e75))
* added registration flow with django-allauth ([eb0d3b2](https://gitlab.com/bubblehouse/django-moo/commit/eb0d3b27b2c07f57aa5500340922047cf179564d))
* added remaining room functions ([2491f79](https://gitlab.com/bubblehouse/django-moo/commit/2491f791560cc45ecb2a4499d029590c7da69444))
* added remaining room functions ([6bdcf08](https://gitlab.com/bubblehouse/django-moo/commit/6bdcf08285d0c3a58eb3b1ea5d7c5237df606fe4))
* added remaining root_class functions, ensure all objects use $root_class if it exists ([14455b8](https://gitlab.com/bubblehouse/django-moo/commit/14455b8306c0a26ca5c68c93b86c03b7d480ca6c))
* added Rich library ([6b1524c](https://gitlab.com/bubblehouse/django-moo/commit/6b1524cf80fdf1658ea329902d7f064287b78423))
* added sftp/scp support for editing verbs and properties ([5c7ae26](https://gitlab.com/bubblehouse/django-moo/commit/5c7ae26a7fb5c87e407595229bcf9f82f01af79d))
* added support for postgresql subchart ([db5776e](https://gitlab.com/bubblehouse/django-moo/commit/db5776e3523b5a4c1bd4865e915fe731959593d3))
* added verbs to enable ssh key management ([45bd563](https://gitlab.com/bubblehouse/django-moo/commit/45bd5636234f7d66012e83c585b2c57c7f31e2ea))
* added verbs to enable ssh key management ([a368894](https://gitlab.com/bubblehouse/django-moo/commit/a368894a7226ddf19ac57bf9f12a454f49ad6ff0))
* allow sending messages directly to a user ([053489c](https://gitlab.com/bubblehouse/django-moo/commit/053489ceb466c36dd3c4ea25aba7df0c0dcaba40))
* began implementing support for background tasks ([d88a56e](https://gitlab.com/bubblehouse/django-moo/commit/d88a56e5e46e76473fee8344945fe0e2147916be))
* begin implementing code execution ([e41e4cb](https://gitlab.com/bubblehouse/django-moo/commit/e41e4cb14f6db49c377733e6c0987d4e3f04cf89))
* begin integrating ACLs ([7373173](https://gitlab.com/bubblehouse/django-moo/commit/7373173095bf765852487c9f06f0dada92ea27a5))
* begin to mimic LambdaCore in the `default` bootstrap configuration. ([5b25dac](https://gitlab.com/bubblehouse/django-moo/commit/5b25dacdb158cf72f0f7bb762b7dd3e5538f009d))
* cache permission tables in the context ([b443541](https://gitlab.com/bubblehouse/django-moo/commit/b443541fc1f619cdf7204d380622439c250479a6))
* configure django/celery intergration ([1f7cbc0](https://gitlab.com/bubblehouse/django-moo/commit/1f7cbc07da8ef4e67356c3761d8dea562e0a69de))
* convert set_default_permissions to a special case, other verb execution optimizations ([c41f06a](https://gitlab.com/bubblehouse/django-moo/commit/c41f06ae0d456c62d8112843d4a8b6f87938348c))
* created core app with model imported from antioch ([95038f0](https://gitlab.com/bubblehouse/django-moo/commit/95038f04601ac892a4830ac94cbdab89d3cc2d5e))
* created db init script ([1a9a1fb](https://gitlab.com/bubblehouse/django-moo/commit/1a9a1fb2cc02d9cf31bd0d51364661c255ae4822))
* created players() primitive and parser.get_search_order() ([8587158](https://gitlab.com/bubblehouse/django-moo/commit/8587158fbf7186a39e8538d2a8e932bb66955708))
* denormalize ancestor lookups, add cross-session property cache, batch verb dispatch (opt-in) ([b5e7c3c](https://gitlab.com/bubblehouse/django-moo/commit/b5e7c3c8e3d7c3c6bd0cb66550f16d307a8c4d52))
* enable Rich-based markup processing on output ([1483a95](https://gitlab.com/bubblehouse/django-moo/commit/1483a957cf9c50bf0cfa971f02af487b1b7a05fd))
* first pass at room movement verbs ([a94ce92](https://gitlab.com/bubblehouse/django-moo/commit/a94ce9230c2f60e0a0b0bf71474979738dd720ec))
* first release to PyPI ([2614bf9](https://gitlab.com/bubblehouse/django-moo/commit/2614bf93fc7a8862042d407ec81876fddc51ce57))
* formally released as django-moo ([dafb610](https://gitlab.com/bubblehouse/django-moo/commit/dafb610a7daab3cd5d7c960b2f925b6856076063))
* fully interactive SSH prompt using `python-prompt-toolkit` ([f5ead2e](https://gitlab.com/bubblehouse/django-moo/commit/f5ead2e54d5165e85cec3a404cd6299873602c2f))
* further optimizations for quick wins, missing indexes ([f35b5e6](https://gitlab.com/bubblehouse/django-moo/commit/f35b5e6387cc4dea3aec8ee97c5805c5a7dd6cec))
* get_property will now recurse the inheritance tree ([f167194](https://gitlab.com/bubblehouse/django-moo/commit/f1671945bb53996bcd9143b58b307f08e0056de1))
* implement a trivial SSH server as a Django Management command ([4c8ba52](https://gitlab.com/bubblehouse/django-moo/commit/4c8ba52112a9a8b0bbb22802cbfb4875280bbbf8))
* implement add_entrance and add_exit, convert dig and tunnel to use those ([9197081](https://gitlab.com/bubblehouse/django-moo/commit/9197081a8fcddae0e86f3fa1640796adbc796907))
* implement getattr support for props and verbs ([f774b8a](https://gitlab.com/bubblehouse/django-moo/commit/f774b8a347ee5c1f916c14aaf2c14855f2fcd98d))
* implement proper permissions and handlers for owners and locations ([f56a9d5](https://gitlab.com/bubblehouse/django-moo/commit/f56a9d59f74c0dc2f767cf2604db8d820fc768ed))
* implement serialization for moo types ([8d7fd98](https://gitlab.com/bubblehouse/django-moo/commit/8d7fd9885aac331870081d6506d18237f9f1644d))
* implemented context.caller_stack to see the list of callers ([e69a75b](https://gitlab.com/bubblehouse/django-moo/commit/e69a75bfa240ab7f88dcb79eb915a4f7d44c112d))
* implemented OUTPUTPREFIX, OUTPUTSUFFIX and .flush. closes [#6](https://gitlab.com/bubblehouse/django-moo/issues/6) ([a863b29](https://gitlab.com/bubblehouse/django-moo/commit/a863b292ef2afc24e93a5c973cee19a18fd84082))
* implemented support verbs for exits ([7d7a58d](https://gitlab.com/bubblehouse/django-moo/commit/7d7a58deec90a589a91d5b6e37d426890d498655))
* implementing container support ([98b9d3f](https://gitlab.com/bubblehouse/django-moo/commit/98b9d3fbdaf06aee829077b87e14aef96d2be6fe))
* improve verb loading ([89a711d](https://gitlab.com/bubblehouse/django-moo/commit/89a711dff616e66fec90b55d486aaab448af56f6))
* improved prompt, some refactoring ([a067dcf](https://gitlab.com/bubblehouse/django-moo/commit/a067dcf81e92fd540fa520343fe989f57b34a11a))
* install a web-based ssh client on the root page ([48d4ca6](https://gitlab.com/bubblehouse/django-moo/commit/48d4ca610b779e8eaa6aa063327ded68f4cac889))
* instead of having the verb name as args[0], make it verb_name ([5469ed4](https://gitlab.com/bubblehouse/django-moo/commit/5469ed4dc5fc0b592498de24ac1e0c9655672c59))
* integrate Python shell with restricted environment ([171c7c7](https://gitlab.com/bubblehouse/django-moo/commit/171c7c7bbdb6bfd1e96679e3a3f38425ecfb2039))
* let specifying verbs and props at the CLI with [@edit](https://gitlab.com/edit) ([8d76e08](https://gitlab.com/bubblehouse/django-moo/commit/8d76e080f1c7b6efaf2e6382d61d55978e4926d7))
* lookup support $var syntax ([d5ef776](https://gitlab.com/bubblehouse/django-moo/commit/d5ef77695135fccea5b4b7fb28f5bf296c12019a))
* lots of DB optimizations for related objects ([577225d](https://gitlab.com/bubblehouse/django-moo/commit/577225d70679615f8a89ce78400340d9e6b27404))
* merged webssh index.html into django for foture expansion ([67b4a67](https://gitlab.com/bubblehouse/django-moo/commit/67b4a67f54a98b58e98a0884d3bafd035ea14772))
* move common boostrap code for universe into initialize_dataset ([63e0a9d](https://gitlab.com/bubblehouse/django-moo/commit/63e0a9d99dc2096c767c4c0602e0a07cb767c957))
* optimized default_verbs to reduce DB calls, introduced better exceptions for verbs ([4fbdef6](https://gitlab.com/bubblehouse/django-moo/commit/4fbdef6d561d6a0f09de7349d09c757a79674b6e))
* ownership and ACL support ([4de1e87](https://gitlab.com/bubblehouse/django-moo/commit/4de1e872ec7f525fca6cf42657dd3f0a915be016))
* permission caching improvements and updated indexes ([4cca41e](https://gitlab.com/bubblehouse/django-moo/commit/4cca41edcf00a4bc19189d20cceb0f28bfc7b478))
* prompt shortcuts, like " to trigger say "" ([413de46](https://gitlab.com/bubblehouse/django-moo/commit/413de46d91660ce354ef98f2f8f5a5e11c70b8dd))
* proper location change behavior, closes [#12](https://gitlab.com/bubblehouse/django-moo/issues/12) ([956760a](https://gitlab.com/bubblehouse/django-moo/commit/956760a1f8dfc1fd3a53ebbbb85b81f5da51c710))
* provide readiness and liveness files ([112d774](https://gitlab.com/bubblehouse/django-moo/commit/112d7745c7472d2b34f22b8cd0728c08809c4b22))
* reduce image size by using a builder image ([ccd2a10](https://gitlab.com/bubblehouse/django-moo/commit/ccd2a10b3f13434828079db5262260957092b1fa))
* refactor moo.core into moo.sdk for verb isolation purposes ([8f0166a](https://gitlab.com/bubblehouse/django-moo/commit/8f0166a5bfea75274992534459e636a84b809b54))
* removed Accessible- proxy objects ([0ac440a](https://gitlab.com/bubblehouse/django-moo/commit/0ac440a144c792297034ad0411fe714ec276e847))
* removed unused Task model ([d66a1c1](https://gitlab.com/bubblehouse/django-moo/commit/d66a1c1be37709ab1939a1bf232162d2b32d1ec0))
* renamed the `api` context variable to just `context` for clarity ([c05a4f5](https://gitlab.com/bubblehouse/django-moo/commit/c05a4f5d28276c67daa6fd83392cb77dddf0c716))
* replace custom pager with pypager ([b208b3d](https://gitlab.com/bubblehouse/django-moo/commit/b208b3de224639f40f1fb5b66fda7e0c3014c1b0))
* replace Django model exceptions with custom ones that are formatted by the parser task ([2009375](https://gitlab.com/bubblehouse/django-moo/commit/2009375936218c64d7558fc0a429e99f30283d65))
* replace O(depth^2) Python recursion in object.py with recursive CTEs; correct parent ordering ([6d8b54a](https://gitlab.com/bubblehouse/django-moo/commit/6d8b54a700c50ccc1c0dd7922c5dcf276f30579b))
* replace temp shell with python repl ([abaf8ce](https://gitlab.com/bubblehouse/django-moo/commit/abaf8ceb2035186036e7dff1862e984af6c1d95c))
* run verb code in Celery workers instead of the web application ([7181f20](https://gitlab.com/bubblehouse/django-moo/commit/7181f20ed0bee4fca05b4a857b866ca6fef89093))
* setup postgres settings for dev and local ([eb3847d](https://gitlab.com/bubblehouse/django-moo/commit/eb3847d0d7755518153db9683fc31bfaa50aca57))
* simplified client code and removed Python REPL ([ef170b5](https://gitlab.com/bubblehouse/django-moo/commit/ef170b51c86c2e00066d84440a9488e409fb30d4))
* ssh prompt now defaults to sentence parser ([f2f4e40](https://gitlab.com/bubblehouse/django-moo/commit/f2f4e403db0ebd4fdf76ecbe40ee49c41189ab2e))
* support `obvious` on objects ([59676b8](https://gitlab.com/bubblehouse/django-moo/commit/59676b8bc56c3537cd154bf6ce17f10efb40e5bd))
* support editor use with describe ([d1a34a9](https://gitlab.com/bubblehouse/django-moo/commit/d1a34a9dce70f7b9b3791fd730b044f4c7b666d1))
* support verb specifiers ([e466da1](https://gitlab.com/bubblehouse/django-moo/commit/e466da18c984bc9791aab8def74c5266e1066c55))
* time limit is overrideable by env var ([70c86ff](https://gitlab.com/bubblehouse/django-moo/commit/70c86ffa6b34b7f80565c0c383925d20b4d9ca5c))
* update helm chart with missing components ([5253873](https://gitlab.com/bubblehouse/django-moo/commit/5253873ee58d4df151fc0847e6896a093366a7b1))
* use a context manager around code invocations ([2bc80ef](https://gitlab.com/bubblehouse/django-moo/commit/2bc80efd2de37323ffb20e9623682b59595bc4b2))
* use ACE editor inside the Django admin for editing Verbs ([da9fd80](https://gitlab.com/bubblehouse/django-moo/commit/da9fd80dd7417365253fbd560fba499d75089df6))
* use correct hostname in webssh when deployed ([b036ecd](https://gitlab.com/bubblehouse/django-moo/commit/b036ecd61192d9bb7f6ee557005883ea0ff03b28))
* use Django user to authenticate ([6b59b74](https://gitlab.com/bubblehouse/django-moo/commit/6b59b7444e633ef3d5259a85596ad086e57d08c6))
* use S3 for static assets ([5e155c9](https://gitlab.com/bubblehouse/django-moo/commit/5e155c91741174dc0143bb99ed50afcbe3720a23))
* use solarized-dark for the code editor ([db8e10b](https://gitlab.com/bubblehouse/django-moo/commit/db8e10b7f86b91c9bdeb8340a39e7e25e949d7fb))
* use the redis result backend when not in testing ([d4bc303](https://gitlab.com/bubblehouse/django-moo/commit/d4bc30357a734dee8c0c01fdb03a6c26d44753f3))
* write() and set_task_perms() can ony be called by Wizard-owned code ([57a8735](https://gitlab.com/bubblehouse/django-moo/commit/57a87354581c039642018a5891891a95a5a9236a))

### Bug Fixes

* --on is required in the moo shebang line ([76be2a1](https://gitlab.com/bubblehouse/django-moo/commit/76be2a1e4fdc2e045a3ac372211dc818eb916535))
* acl __str__ verb refs ([8dc6caf](https://gitlab.com/bubblehouse/django-moo/commit/8dc6cafc46cde17cb700ec628892458649ab49dc))
* active user not so simple ([e07c4cb](https://gitlab.com/bubblehouse/django-moo/commit/e07c4cbb5822d082fbdfee6b774a9fa3a590dc85))
* add black to dependencies and update agent docs ([9b86be4](https://gitlab.com/bubblehouse/django-moo/commit/9b86be4243c60cb427a7add79a7fc1df56a2764a))
* add default OTEL_SERVICE_NAME to chart ([87f6be2](https://gitlab.com/bubblehouse/django-moo/commit/87f6be240f3ffca2bb2764de19dabd63e6fb3055))
* add owner variable to add_* methods ([e1276a8](https://gitlab.com/bubblehouse/django-moo/commit/e1276a8fa35e4139888dcd01cf7ecf84b93ae268))
* add Player model for User/Avatar integration ([3f19b33](https://gitlab.com/bubblehouse/django-moo/commit/3f19b3313768031544bff2085fadb8a93b2d25ec))
* add Player model for User/Avatar integration ([8b369c4](https://gitlab.com/bubblehouse/django-moo/commit/8b369c4b07174b8a4fef5c2764807dd07749be3b))
* add some missing fields, include extras in the package so it can build a Docker container ([8e59fd1](https://gitlab.com/bubblehouse/django-moo/commit/8e59fd1f5a5b5efc352280ab1ba939c1fafe4b34))
* add viewport meta tag to fix mobile ([48f8da7](https://gitlab.com/bubblehouse/django-moo/commit/48f8da70825f7363b90a2328860afd9c0f26a304))
* add_propery and add_verb updates ([3e8b492](https://gitlab.com/bubblehouse/django-moo/commit/3e8b4928cec2cff8dfa415fc4a7fa1c81f3e3fd9))
* added additional args to callback ([d115960](https://gitlab.com/bubblehouse/django-moo/commit/d115960ede6d2773c6d6f9ebacf7edf8be8ebd02))
* added admin panel for Relationship for spurious reason that might never happen again ([33a1ead](https://gitlab.com/bubblehouse/django-moo/commit/33a1eadb815cab8e5d62a3f0abb76750ca850ef0))
* added correct redis_cache package ([cd616c2](https://gitlab.com/bubblehouse/django-moo/commit/cd616c2d7219e6ee4927ed39d618563f5ff9389f))
* added db_index to important fields ([33ec6b5](https://gitlab.com/bubblehouse/django-moo/commit/33ec6b553d4460eb3eea94700696b30468408e39))
* added DjangoMOO to page title ([db12414](https://gitlab.com/bubblehouse/django-moo/commit/db1241431477ba6bb6ec945a92b98d2e73bb27d7))
* added migration to remove old proxy objects, renamed inherited to inherit_owner, other leftover ([b7947bf](https://gitlab.com/bubblehouse/django-moo/commit/b7947bf98302659a7ab7d2ef41db6277188c2cdb))
* added missing django-compressor dependency ([b94b803](https://gitlab.com/bubblehouse/django-moo/commit/b94b803f9cbf78d4430bc96af68682f8f4fff8e5))
* added missing django-storages dependency ([3f09185](https://gitlab.com/bubblehouse/django-moo/commit/3f09185c0680cc556c64e2b553aac6700038cfe2))
* added missing lookup() function ([ce9c23f](https://gitlab.com/bubblehouse/django-moo/commit/ce9c23fe724a5137e1e0ce3a5ca007204b960ac2))
* added missing params for helm push ([be4d8b7](https://gitlab.com/bubblehouse/django-moo/commit/be4d8b7fdd234f86a5a7fa0ecb0b3e34a61c5023))
* added missing remove_parent method, bug in `entrust` handling ([6fd667a](https://gitlab.com/bubblehouse/django-moo/commit/6fd667af1e16a2d9902427ffed14c07c5d0f67b6))
* added missing setting ([b54c6f6](https://gitlab.com/bubblehouse/django-moo/commit/b54c6f6dfb39f3870639595205d1ae70fd60e66d))
* added more safe builtins ([51553ae](https://gitlab.com/bubblehouse/django-moo/commit/51553aef035956e2435bf87c92b9dd692d337a24))
* added redis_cache dependency, setup caches in dev ([cfa14ea](https://gitlab.com/bubblehouse/django-moo/commit/cfa14ea5f6fd1c1c6983b09c41a008480d204e5a))
* added stub obj.is_connected() for later implementation ([ae4551c](https://gitlab.com/bubblehouse/django-moo/commit/ae4551c22905c0f1c12826b267ae0a3d353f813c))
* added trivial implementation of $room.tell_contents for now ([7035690](https://gitlab.com/bubblehouse/django-moo/commit/7035690abf6a33caafbe2ff417edb7087108ef1a))
* additional caching and go improvements ([cade791](https://gitlab.com/bubblehouse/django-moo/commit/cade791fb51d9150053f3b459185c0f475f431d0))
* aliases work inside the parser now ([37b41c6](https://gitlab.com/bubblehouse/django-moo/commit/37b41c60eb0355ca8c8b15f58a0030c7edd5bd76))
* allow login form to wrap on smaller screens ([003b7cd](https://gitlab.com/bubblehouse/django-moo/commit/003b7cde54f9cf6634deff212a17061fbdc7e93b))
* allow more look scenarios, update test ([b2f1524](https://gitlab.com/bubblehouse/django-moo/commit/b2f15242498afedcaa253461de3dedddb4f568b4))
* allow use of external packages, update docstrings ([527f04a](https://gitlab.com/bubblehouse/django-moo/commit/527f04a0f6cab1f1aba26720fdf809952561a69a))
* allow use of the type() builtin ([9bcabb2](https://gitlab.com/bubblehouse/django-moo/commit/9bcabb205fb49c4b71a9c6340185ecf0d0fc8635))
* almost removed AccessibleObject model ([5ca065b](https://gitlab.com/bubblehouse/django-moo/commit/5ca065b1b245408d1c7e6099773b79fc36cc82cb))
* always use Accessible- objects if they will be used in a restricted env ([7ddbc1c](https://gitlab.com/bubblehouse/django-moo/commit/7ddbc1c40b8a57a2852958c8aab8bb1865ff4c6d))
* avoid pinning Python version, include wheel as release attachment ([f696e6b](https://gitlab.com/bubblehouse/django-moo/commit/f696e6bc52eb98f14411762ea75d06002b676b6e))
* be clear about which dataset is being used ([37fceb7](https://gitlab.com/bubblehouse/django-moo/commit/37fceb7a5ffd4b2a1f5ac107ddf698ccbc2e7878))
* bootstrap naming tweaks, trying to add first properties with little success ([7b21c97](https://gitlab.com/bubblehouse/django-moo/commit/7b21c971117ce0f55efa6cf9f543c7697d7ecff4))
* bootstrapping issues, refactoring ([80b7168](https://gitlab.com/bubblehouse/django-moo/commit/80b7168026b16911fc428ee9750682675b70160e))
* broken BBcode colors ([dcba378](https://gitlab.com/bubblehouse/django-moo/commit/dcba378f0bf497142b90ea578f9a2a0a0dd0f524))
* broken tests ([861d8ea](https://gitlab.com/bubblehouse/django-moo/commit/861d8eaa8d43e570be31b362f2163a3f1e4bf363))
* call confunc and disfunc properly ([8afffac](https://gitlab.com/bubblehouse/django-moo/commit/8affface2039fe618ff1b1f13e03bb300cf5dbe3))
* change migration and collectstatic to pre-hooks ([cc917b7](https://gitlab.com/bubblehouse/django-moo/commit/cc917b71547c1c4ef42f75a1a485793943a2ae96))
* change ownership of server key ([19b3a57](https://gitlab.com/bubblehouse/django-moo/commit/19b3a578d6317b85f3734b5ee2c59f873f5f4fb6))
* changed location of chart ([9f45a2c](https://gitlab.com/bubblehouse/django-moo/commit/9f45a2c36f42a608158d613176f75cf84acd9f05))
* chart semantic-release version ([5625230](https://gitlab.com/bubblehouse/django-moo/commit/5625230d0b8aa9351b4059e462d98e0e79110245))
* chart semantic-release version missing files ([ab2744e](https://gitlab.com/bubblehouse/django-moo/commit/ab2744e1c47fb2f7e0ac44cfdd4549ad20529dd9))
* chart semantic-release version missing files ([65c4b9b](https://gitlab.com/bubblehouse/django-moo/commit/65c4b9ba99e0094481621c35f3e60cd5a976c1a1))
* chart typo ([08e41d5](https://gitlab.com/bubblehouse/django-moo/commit/08e41d5f834d38fcc0460aa3496985a9065b70dd))
* chart typo ([e5e74d9](https://gitlab.com/bubblehouse/django-moo/commit/e5e74d9cc39d1daa16897b09bcc4c786e974dd95))
* check for recursion when changing location ([0606dad](https://gitlab.com/bubblehouse/django-moo/commit/0606dad30b6c3a746d1387923a6f638f29f79a1c))
* class name consistency ([ea75ecd](https://gitlab.com/bubblehouse/django-moo/commit/ea75ecd621c28bcae5df1d20814fc6423c377caa))
* cleaned up invoke_verb, added docs ([645d9b9](https://gitlab.com/bubblehouse/django-moo/commit/645d9b9bafb5ba2a9372efabd5e285fceec387d6))
* commit to force release ([8d25cf2](https://gitlab.com/bubblehouse/django-moo/commit/8d25cf23a51dc0bcb331316fdeec52e0018874f0))
* configure logging ([b438e42](https://gitlab.com/bubblehouse/django-moo/commit/b438e421a4fdc3611685513b8a0af7cf894967f0))
* consolidate custom verb functions in moo.core ([611fa57](https://gitlab.com/bubblehouse/django-moo/commit/611fa57edeb05ffc38fc85c194d3b63480fa42e3))
* continuing to address init issues ([35b1fb1](https://gitlab.com/bubblehouse/django-moo/commit/35b1fb10bb169f5ef4d10b3e01c26be1f6ef76fa))
* correct escaping in at_describe ([90b82f8](https://gitlab.com/bubblehouse/django-moo/commit/90b82f8e5ddcd01bae01532f7a9322ba4efcd4e6))
* correct verb handling scenarios ([f5f91f2](https://gitlab.com/bubblehouse/django-moo/commit/f5f91f283ccd5ff9b20a518f03104cf530d0abe9))
* correctly clone instances ([b2732cc](https://gitlab.com/bubblehouse/django-moo/commit/b2732cc53a7c9c2e8bb3f37761ba09ac2633915a))
* correctly handle ctrl-D ([25e908f](https://gitlab.com/bubblehouse/django-moo/commit/25e908f757de7b8d6a8c3782b7568f9eb3a5871e))
* create use objects by default so Wizard group rights work ([796327c](https://gitlab.com/bubblehouse/django-moo/commit/796327ca5e2c59f1ad10b94c6642a5a87f3791d2))
* dependency fix for redis, move import ([46280f0](https://gitlab.com/bubblehouse/django-moo/commit/46280f09f7450c8d6bcbf99675381f924072f7f4))
* disable liveness/readiness for ssh server for now ([90c7bb6](https://gitlab.com/bubblehouse/django-moo/commit/90c7bb6659b7ece47809b470df2253d010bc8b3d))
* disable Redis in unit tests to avoid blocking issues ([49a1f28](https://gitlab.com/bubblehouse/django-moo/commit/49a1f28f56a6bb3d435b745422226f184f0f2a37))
* disabled DBs and cache temporarily in dev, moved around environment names ([dd502d9](https://gitlab.com/bubblehouse/django-moo/commit/dd502d9d9f2858d6433b44942a3e22d4ea17b018))
* don't use parallel cmake builds if you like your homelab ([4f20db2](https://gitlab.com/bubblehouse/django-moo/commit/4f20db28a087a0aba01d267833268ce09a30368f))
* don't use poetry inside Docker ([6589954](https://gitlab.com/bubblehouse/django-moo/commit/6589954bf46dcd9829479b11f507919161964853))
* dont include self in tell_contents() ([aac83c3](https://gitlab.com/bubblehouse/django-moo/commit/aac83c32c9417815cea46742eade35b35da71d4d))
* dont load from a file when the code is provided ([00d51eb](https://gitlab.com/bubblehouse/django-moo/commit/00d51ebb535fc2851cbe08adb6ea9b71248cf11c))
* dont massage verb code in prompt ([465bdf9](https://gitlab.com/bubblehouse/django-moo/commit/465bdf9d5fb92d112c45ea89d8d6cce7e4b7734e))
* dont print tracebacks for UserErrors, even to wizards ([4036dbd](https://gitlab.com/bubblehouse/django-moo/commit/4036dbd302787eff3478dfd0c5280658860b8636))
* dont remove shebang when bootstrapping ([e7aa635](https://gitlab.com/bubblehouse/django-moo/commit/e7aa63553cc8accde178903b026ff04f0da785f9))
* dont stringify things being printed ([999bb0c](https://gitlab.com/bubblehouse/django-moo/commit/999bb0c9208fdd9ba6de8c0e7771618460b61aed))
* dont try to install native python modules ([d80cae5](https://gitlab.com/bubblehouse/django-moo/commit/d80cae501b874e19c0c943a75a92e8853754dace))
* dont use /var/run ([1fc28e8](https://gitlab.com/bubblehouse/django-moo/commit/1fc28e8a704063f219b0fa19366ba0d1be454318))
* dont use /var/run ([5dcddc9](https://gitlab.com/bubblehouse/django-moo/commit/5dcddc9bbf9c2d1ef825b60bc766cdc2c5f6a4c8))
* door locking issues resolved ([c7734d9](https://gitlab.com/bubblehouse/django-moo/commit/c7734d9d8244f9fdce34bbb34ee78039933b5abf))
* enable batch verb dispatch ([af260eb](https://gitlab.com/bubblehouse/django-moo/commit/af260ebb4df288ad17677157433a5be97bb9771a))
* enable post-quantum key exchange in SSH server ([f685019](https://gitlab.com/bubblehouse/django-moo/commit/f685019a53b6ea6757484b722c1f3a911751ff2d))
* enable post-quantum key exchange in SSH server ([15fba14](https://gitlab.com/bubblehouse/django-moo/commit/15fba14b0d169c196bffc1c7e90c74e72775f19b))
* ensure all verbs will be bound before execution, raise exception otherwise ([03a2b18](https://gitlab.com/bubblehouse/django-moo/commit/03a2b18df8f92de9ca01ecefb4fb7d7f93d1926d))
* ensure we always get an accessible object here ([efe9b67](https://gitlab.com/bubblehouse/django-moo/commit/efe9b673a2a372a3709bc033b2b892121d12fc0e))
* exits shouldn't be literally inside the rooms they connect to ([a670319](https://gitlab.com/bubblehouse/django-moo/commit/a6703196037a1bbb254fdb193de03dbe89556c1c))
* extend job timeout ([8bd0bd5](https://gitlab.com/bubblehouse/django-moo/commit/8bd0bd50599efe989160b517733e3d8098a35a37))
* final issues with verbs in debugger ([b741313](https://gitlab.com/bubblehouse/django-moo/commit/b7413135dd8f76453778f205e5efeac01b954535))
* fixed remaining caller_stack issues ([b281873](https://gitlab.com/bubblehouse/django-moo/commit/b2818734bb9b81bd1eab4d67df5cdc9c4bba49fb))
* fixed remaining test issues ([d9490fd](https://gitlab.com/bubblehouse/django-moo/commit/d9490fd7d3a861751c738c0ae866a18cdd14bf7e))
* fixed use of args/kwargs with multiple verb invocations ([f400b7f](https://gitlab.com/bubblehouse/django-moo/commit/f400b7f345001b26395c7c05366b5f7f54b3a627))
* fixes for permissions and associated tests ([4475a95](https://gitlab.com/bubblehouse/django-moo/commit/4475a95f5db111aee86348c746e30c51e1e63d40))
* fixes found during testing ([5a90497](https://gitlab.com/bubblehouse/django-moo/commit/5a90497aefb53a6c6a6460b598cb339e607ce905))
* force release ([044e0b9](https://gitlab.com/bubblehouse/django-moo/commit/044e0b938ec3ca8ff71dfffcb9def429ec22765b))
* force release ([2202c5a](https://gitlab.com/bubblehouse/django-moo/commit/2202c5a945a6350e5541be334cbefe049a0fddd0))
* force release ([b87e4d1](https://gitlab.com/bubblehouse/django-moo/commit/b87e4d14ec8296c10f018a88dab32422ffde669c))
* force release ([0bd5896](https://gitlab.com/bubblehouse/django-moo/commit/0bd58967abb6d66d5ce6e39da8f9d8e9bd588fc7))
* force release ([d7cf6de](https://gitlab.com/bubblehouse/django-moo/commit/d7cf6de23672e972a1188548478dab14670810c6))
* force release ([ce29dd3](https://gitlab.com/bubblehouse/django-moo/commit/ce29dd321d6c6124f5113496e7b3c60cd584a904))
* force release ([e6d53dc](https://gitlab.com/bubblehouse/django-moo/commit/e6d53dc6e93f856971db794a8b7dcb7adb194d64))
* force release ([0bf2554](https://gitlab.com/bubblehouse/django-moo/commit/0bf255449905f917d9481e3a199b9d89534c861f))
* force release ([3eb5f53](https://gitlab.com/bubblehouse/django-moo/commit/3eb5f53028c85ad174fc8bdf9d944e73c68f0eff))
* force release ([7d29873](https://gitlab.com/bubblehouse/django-moo/commit/7d29873b67336fb423afa61c5e9ef83f9adce8c2))
* frame access exploit and str.format issue, block modules ([b1aca81](https://gitlab.com/bubblehouse/django-moo/commit/b1aca8197c128d9de4d37e70e7bdd5e9a60d34f4))
* further improvements to syntax sugar ([5afe0c6](https://gitlab.com/bubblehouse/django-moo/commit/5afe0c6cede47eaff799b1495b4298eb9b39968a))
* further ssh improvements ([d1cf836](https://gitlab.com/bubblehouse/django-moo/commit/d1cf836e532c8e22691cda18fa082270a119c93b))
* generate a key inside the Dockfile ([afb9efb](https://gitlab.com/bubblehouse/django-moo/commit/afb9efb6aaefcac846c23696aeda91c0a692843a))
* generate a key inside the Dockfile ([1384160](https://gitlab.com/bubblehouse/django-moo/commit/1384160f7e0ce70840559731e90bbcc01b3ba085))
* getattr support for props and verbs ([a6301d6](https://gitlab.com/bubblehouse/django-moo/commit/a6301d6a2cd000f806bafb42a5a03d15cfac78be))
* go verb needs to save the changes to caller location ([86fcbf6](https://gitlab.com/bubblehouse/django-moo/commit/86fcbf6d15386717e0e58c898dcc397b0d84007a))
* handle direct object ID lookups ([b3b9571](https://gitlab.com/bubblehouse/django-moo/commit/b3b9571d301d930a9fd79eed35e5a9c7d327a9af))
* handle encoding consistently ([97e1991](https://gitlab.com/bubblehouse/django-moo/commit/97e19912ad103e1d4107a83f019bef2e9659476b))
* handle prompt when user is nowhere ([49d8c6f](https://gitlab.com/bubblehouse/django-moo/commit/49d8c6f50f7ef22f7e5e30f244f3a75a4f0b2ac6))
* handle RESERVED_NAMES properly ([bcb79ce](https://gitlab.com/bubblehouse/django-moo/commit/bcb79ceb0c0cc2d806eb1fc1742d7dd0dfeb989b))
* handle unallocated users in write() ([7b47ca1](https://gitlab.com/bubblehouse/django-moo/commit/7b47ca141d440bd78ff6331b809b3b34cfcc4dff))
* handle uncaught test warnings ([acbd0c6](https://gitlab.com/bubblehouse/django-moo/commit/acbd0c683489f13dfecea60422043a7e0f5a3eca))
* handle verb names in methods properly ([570a3be](https://gitlab.com/bubblehouse/django-moo/commit/570a3be23f65dadf37bd1f8dffd64ccdd4598d49))
* hard-code hostname and port for webssh ([87b5b63](https://gitlab.com/bubblehouse/django-moo/commit/87b5b63064917c3233c64106e1b80b98c3a1956a))
* helm chart selector labels for shell service ([78751d9](https://gitlab.com/bubblehouse/django-moo/commit/78751d9eeeb95808ed5b05780718102b3fa9320d))
* hold on to get/set_caller until we have a replacement for verb to use ([26eaeb7](https://gitlab.com/bubblehouse/django-moo/commit/26eaeb711fff495ed15c71b1bc1bb69e50fe6a5e))
* ignore methods when parsing for verbs ([194e061](https://gitlab.com/bubblehouse/django-moo/commit/194e061065cd120bb57e19750272a35d3f25bdbc))
* implementing more permissions details, refactoring ([b832a85](https://gitlab.com/bubblehouse/django-moo/commit/b832a85bb308649f86254e63452ca318dc97afff))
* improve create when using args ([5d1a41c](https://gitlab.com/bubblehouse/django-moo/commit/5d1a41c1ee1490245efd963ed2920cdb20ec5dd4))
* improve describe verb and add test ([51d81a2](https://gitlab.com/bubblehouse/django-moo/commit/51d81a26a45d2cecd3cd8fecf7404c42da9de15b))
* improve exception handling by parser ([df89962](https://gitlab.com/bubblehouse/django-moo/commit/df899625a143422b4009c0aa404ee4272f5ced0e))
* improve method handling to handle system.describe() implementation ([a8568bd](https://gitlab.com/bubblehouse/django-moo/commit/a8568bdca86d716bcfa0d8d95f9cc677c147f2d9))
* improve title of editor ([75421e5](https://gitlab.com/bubblehouse/django-moo/commit/75421e5b12e5bcce6d68ebd23a8c549d2ffcbaaf))
* improve var handling ([f24235c](https://gitlab.com/bubblehouse/django-moo/commit/f24235cd1f38f8b5785e7265d6ba375f3ee22799))
* improve verb write handling ([69776d6](https://gitlab.com/bubblehouse/django-moo/commit/69776d61216a5a7ff0378bfae3853e1dc658cb59))
* improved `look` command with better functionality and ANSI colors ([a1e5693](https://gitlab.com/bubblehouse/django-moo/commit/a1e56934fe7ab450bf9578d7ce18350592e3d766))
* include repo for reloadable verbs ([e0a3004](https://gitlab.com/bubblehouse/django-moo/commit/e0a30042f988eaa601479eb548678f9320aa6850))
* include subchart ([e76f144](https://gitlab.com/bubblehouse/django-moo/commit/e76f14490654826d9e4e371642fd4ccbbe230071))
* incorrect is_bound() handling ([5a11537](https://gitlab.com/bubblehouse/django-moo/commit/5a115378e7b707c91dd3eb2794e158720d3b1343))
* index name too long ([9ca4f55](https://gitlab.com/bubblehouse/django-moo/commit/9ca4f555c4e7545536fb926518f0d91cad9d3999))
* ingress port correction ([1ce664f](https://gitlab.com/bubblehouse/django-moo/commit/1ce664fb34b56e27204cedf703e2fef4a3eb2cfc))
* install django-extensions for debug purposes ([deaf6ff](https://gitlab.com/bubblehouse/django-moo/commit/deaf6ffc0c58d6181ac14a75e4b8b7be848f72ed))
* install django-extensions for debug purposes ([47234e1](https://gitlab.com/bubblehouse/django-moo/commit/47234e152e3487831730bfcc81861f74e316c102))
* install django-extensions for debug purposes ([ada3302](https://gitlab.com/bubblehouse/django-moo/commit/ada3302ea7a4168fa4a53493cf15c30f450635f9))
* install ssh ([24354fe](https://gitlab.com/bubblehouse/django-moo/commit/24354fe495a777111a27aa3076da45d36434df1c))
* install uv ([05cf565](https://gitlab.com/bubblehouse/django-moo/commit/05cf565070d165ae0658b27d707f744eb7274525))
* install uv ([6b83a7c](https://gitlab.com/bubblehouse/django-moo/commit/6b83a7c8dd59f8f13de079f4b6aa754e08a1aaf9))
* installed boto3 ([fa74ac5](https://gitlab.com/bubblehouse/django-moo/commit/fa74ac5868a0bfca9a487684dfb884f6cb79739d))
* installed uwsgi-python3 and net-tools ([debabfd](https://gitlab.com/bubblehouse/django-moo/commit/debabfdcd8611cda4aaeb68147fa86c1f406bef3))
* instead of trying to use contextvars within a thread, just pass the user_id along ([2a93875](https://gitlab.com/bubblehouse/django-moo/commit/2a93875274436ef47a9b72f907390915398a0c27))
* interchangeable prepositions are now working ([b20f21a](https://gitlab.com/bubblehouse/django-moo/commit/b20f21aceef40107a1e4ca9c27a63dbf95bf902b))
* issues found while unit testing, merge old room integration test into new file ([72ece51](https://gitlab.com/bubblehouse/django-moo/commit/72ece51104edf3aa01411d83200143de2fa9b8df))
* issues in take/get for player ([dc2a7ea](https://gitlab.com/bubblehouse/django-moo/commit/dc2a7eade7e363006bcbfd08d58155814853f42e))
* its okay to save the whole model object ([d1282f9](https://gitlab.com/bubblehouse/django-moo/commit/d1282f92dff7c716363a27eb7ddac956a9966a51))
* linting errors ([f80c483](https://gitlab.com/bubblehouse/django-moo/commit/f80c483c9f1c40aa5bc28ba336b296cec2016d5a))
* linting issues ([553eb9f](https://gitlab.com/bubblehouse/django-moo/commit/553eb9f692d1005fc4a94507ad7f849c77b828f0))
* logging improvements ([6c0a391](https://gitlab.com/bubblehouse/django-moo/commit/6c0a3915c1edece13411401ae63bd0037c45703f))
* logging improvements for shell server ([a5b5dd4](https://gitlab.com/bubblehouse/django-moo/commit/a5b5dd40309f68c2ce82b763c2459c938ce1118e))
* logging improvements for shell server ([7d48c7b](https://gitlab.com/bubblehouse/django-moo/commit/7d48c7b234d0772d5a427e289a452c98d38bb722))
* lookup() should understand pronouns ([8139105](https://gitlab.com/bubblehouse/django-moo/commit/81391055adcf834733e909b5337097951e72ce25))
* major permissions fixes by adding player (which is static) vs caller (which can change) ([35f5bdf](https://gitlab.com/bubblehouse/django-moo/commit/35f5bdf74e6893582ad5bcb87bfbc7f972fb8938))
* make exceptions available through moo.core ([dc7c16a](https://gitlab.com/bubblehouse/django-moo/commit/dc7c16a306287c35277968b82007f47913c8065c))
* make get ancestors/descendents generators so we can stop once we find something ([00082ed](https://gitlab.com/bubblehouse/django-moo/commit/00082ed3cf05cf0a83d78e114fb095e434fc296e))
* mangled env fix, ci update ([5557599](https://gitlab.com/bubblehouse/django-moo/commit/55575993fa0d02b0691e3763a4f3f369b105fbe4))
* many fixes for player commands ([1481717](https://gitlab.com/bubblehouse/django-moo/commit/1481717d954a45530ea3b5f01c8c74b831e9d276))
* many sandbox escape vectors identified and sealed ([018d4b8](https://gitlab.com/bubblehouse/django-moo/commit/018d4b82b7e59ca3ee0d7bcebb7cf3b99a0b48ae))
* match_object improvements ([0fbb6ca](https://gitlab.com/bubblehouse/django-moo/commit/0fbb6ca76955f87c87f073df1f79a2b9e3e1758a))
* missing arg in signup method ([0e7ecc4](https://gitlab.com/bubblehouse/django-moo/commit/0e7ecc4c197451cef64d227b5a2ed300bd22c7e3))
* missing f-string prefix ([ef53e4d](https://gitlab.com/bubblehouse/django-moo/commit/ef53e4dad214af20d7bc6c3cfd0c49c189c7bd5b))
* mixed up service ports ([656243a](https://gitlab.com/bubblehouse/django-moo/commit/656243acf02a9284f08dbf4a326f5ed62c612480))
* more sandbox escapes ([bc444ae](https://gitlab.com/bubblehouse/django-moo/commit/bc444ae6f765c1ae3e3c8ff56670a26571efe94a))
* more sandbox escapes for ORM ([e8ae178](https://gitlab.com/bubblehouse/django-moo/commit/e8ae178ab6d1a901a87c15727ce904a6275451d6))
* more sandbox escapes, removed some superflous tests ([edc070f](https://gitlab.com/bubblehouse/django-moo/commit/edc070f106cf4e71c2a6fd564861ef5cbd18aaf6))
* more setup and Django settings refactoring ([e6ca939](https://gitlab.com/bubblehouse/django-moo/commit/e6ca9393a96b2d92ac55b017909bf9a1a126fa1d))
* more verb reload updates ([f137d41](https://gitlab.com/bubblehouse/django-moo/commit/f137d41a23b2bc753bcab9db5523c6ec8d7982ee))
* move player setup into dataset_initialize ([176f017](https://gitlab.com/bubblehouse/django-moo/commit/176f017a33ceafc5855ac5ebe071e216211bcd36))
* moved getattr override to main Object model ([f3b8b73](https://gitlab.com/bubblehouse/django-moo/commit/f3b8b73efb8de0a4416ba87104dfa8dc3c7a64f9))
* moved look to room, parser now calls huh on failure ([063000a](https://gitlab.com/bubblehouse/django-moo/commit/063000a3e8a600f18ac77b329485e64eddd54bba))
* moveto has no underscore ([d426558](https://gitlab.com/bubblehouse/django-moo/commit/d426558fa66e3ef775be92fe26c2a545e1c7f67b))
* only generic exits should be in location None, objects used as doors should not be moved ([98aae52](https://gitlab.com/bubblehouse/django-moo/commit/98aae5258ff0e3892e63d1fede7bbb27ab588595))
* only run watchedo on moo_shell invocations ([540071c](https://gitlab.com/bubblehouse/django-moo/commit/540071c244adf214e69c6248e491e2436b4a5371))
* optimize is_allowed ([37af771](https://gitlab.com/bubblehouse/django-moo/commit/37af771fb54f6c4e5e0f6b76f8562373768dd229))
* other login fixes, still having exec trouble ([8ef3b58](https://gitlab.com/bubblehouse/django-moo/commit/8ef3b58388bba1a1742b3ebdf9ae674ab39c2a53))
* output now sent to client instead of log ([fbf4a9f](https://gitlab.com/bubblehouse/django-moo/commit/fbf4a9feb8b05e10ec3bf99800f15ef9578d63b0))
* override delete() on Object, not AccessibleObject ([657c1e8](https://gitlab.com/bubblehouse/django-moo/commit/657c1e8d7500594361cc99b8bb3a4d6477dcfe79))
* packaging naming ([488c31c](https://gitlab.com/bubblehouse/django-moo/commit/488c31cf1a822ec598168c658785be78a97f83a8))
* parser bugs for unusual situations ([93b458b](https://gitlab.com/bubblehouse/django-moo/commit/93b458bcf6c80294b883c65945c6b598fa64960c))
* parser token should be set to none in every context ([f10eedc](https://gitlab.com/bubblehouse/django-moo/commit/f10eedc10ed33fb5948f1408b474688aaf1a9c86))
* parser.find_object() searches the player inventory first, then the current location ([b04a3c9](https://gitlab.com/bubblehouse/django-moo/commit/b04a3c96c10fe4f9229c7baea4dd2242a4407e64))
* port for shell service ([80a029d](https://gitlab.com/bubblehouse/django-moo/commit/80a029db329c5c716b037e7370c790927b826056))
* port updates ([92c1b6a](https://gitlab.com/bubblehouse/django-moo/commit/92c1b6a764a8042250c07d52c1ae0c00e35ec8b6))
* possessive noun lookup IndexError in Parser.find_object ([d8a117a](https://gitlab.com/bubblehouse/django-moo/commit/d8a117a154d21f6cf6bad12e24e376013a1fc76b))
* pre-import moo.sdk.* when running [@eval](https://gitlab.com/eval) ([b1f2a82](https://gitlab.com/bubblehouse/django-moo/commit/b1f2a82a54845e23fc527ab7198f7036e1c6cc76))
* prepositions and handle query sets ([d3ec915](https://gitlab.com/bubblehouse/django-moo/commit/d3ec9152f1360686b221f4b1a07bd5961cb6ef02))
* preserve player context when invoking verbs asynchronously ([651365b](https://gitlab.com/bubblehouse/django-moo/commit/651365b58adf42e5b9fbe3ce603bfa41d5ba144b))
* prevent Verbs from being called by the admin template engine ([a0f70dc](https://gitlab.com/bubblehouse/django-moo/commit/a0f70dcf8bd9f3926d051ef24bd1b4038b20e9cf))
* prevent wssh from being hijacked for other connections ([0550700](https://gitlab.com/bubblehouse/django-moo/commit/055070075151acdc9058b383b1758fe7fd4ebc5b))
* prompt correctly updating from DB ([7887be6](https://gitlab.com/bubblehouse/django-moo/commit/7887be6419ebbb59d7e85accea8e61e02b103a62))
* prompt improvements ([f75a6ec](https://gitlab.com/bubblehouse/django-moo/commit/f75a6ec6c6e6bd0bf03dc035e683272942f84593))
* proper filename handling fixes debug issues ([1851848](https://gitlab.com/bubblehouse/django-moo/commit/18518489011801409ad815a0e9da5e88dbb7e5bd))
* properly display the first output (look_self) ([9547f9d](https://gitlab.com/bubblehouse/django-moo/commit/9547f9d58175909fc135a203e2313d034d076ef6))
* properly handle set_task_perms ([79de446](https://gitlab.com/bubblehouse/django-moo/commit/79de446128dc27dbeb38f073325e51546551528b))
* properties are not readable by default ([c871a9d](https://gitlab.com/bubblehouse/django-moo/commit/c871a9d7160829dd18dccb7ed1ac90e039ea42ad))
* properties are not readable by default ([3b877f5](https://gitlab.com/bubblehouse/django-moo/commit/3b877f56838cd0eb0191d3937b628774ee0130d4))
* propertly handle "dark" rooms ([9351fcf](https://gitlab.com/bubblehouse/django-moo/commit/9351fcf8a6296cc1de9851bc7747422de8d8604c))
* provide an output for the context ([03fbd70](https://gitlab.com/bubblehouse/django-moo/commit/03fbd70f06a915f77c2af056c6e6e3c6c62d8c3b))
* quiet build warnings about this plugin ([9c28560](https://gitlab.com/bubblehouse/django-moo/commit/9c2856048e6513d43a98e3633decfa3041d09ff9))
* quiet down celery ([8fff0a8](https://gitlab.com/bubblehouse/django-moo/commit/8fff0a8234e33af172223055cdc48485020119d5))
* quiet down nginx, restore redirect ([c73fb1f](https://gitlab.com/bubblehouse/django-moo/commit/c73fb1ff21e4eb8b1dfb9408e9e1b98764b7d7cc))
* raw id field ([b6b1af1](https://gitlab.com/bubblehouse/django-moo/commit/b6b1af1e54d35718dad7fddd4440043ecbbc6156))
* raw id field ([5e777a7](https://gitlab.com/bubblehouse/django-moo/commit/5e777a77e2b82aec195a38d0374eda51a373f6ed))
* readiness typo ([2b3a37f](https://gitlab.com/bubblehouse/django-moo/commit/2b3a37f0c32b10de2954ca965ce9f273ee83ab12))
* redis typo ([25a2b4e](https://gitlab.com/bubblehouse/django-moo/commit/25a2b4e610947bae9135343f6a17863131fb361b))
* registration style and flow issues ([193847d](https://gitlab.com/bubblehouse/django-moo/commit/193847ddc85f2077956e9d474cc2c6b421e48bed))
* reimplementing exits ([0696f8b](https://gitlab.com/bubblehouse/django-moo/commit/0696f8b99c90181570fb30d55c4a92fe7f70a860))
* reimplementing exits ([57c5d4f](https://gitlab.com/bubblehouse/django-moo/commit/57c5d4f1a87605c0803e2dad7f28a5336a1277ae))
* remove broken redirect ([1b9b1ec](https://gitlab.com/bubblehouse/django-moo/commit/1b9b1ec5f2cec665febf6285d65d69f5e0a4245e))
* remove invalid/unneeded related names ([0c99940](https://gitlab.com/bubblehouse/django-moo/commit/0c99940b3684df55a30600de91c8e9145ed8187a))
* remove invalid/unneeded related names ([772538f](https://gitlab.com/bubblehouse/django-moo/commit/772538f3c32565a6aed7a6b9ae0f41126498d512))
* remove magic variables ([7916d17](https://gitlab.com/bubblehouse/django-moo/commit/7916d178c48732d00dbcf4ded1663e51523efb43))
* remove observations, that concept doesnt exist here ([c2d7da3](https://gitlab.com/bubblehouse/django-moo/commit/c2d7da33e15d32bc376570be551aaee1fb8bbaf4))
* remove os.system() loophole and prep for further customization ([91cbcff](https://gitlab.com/bubblehouse/django-moo/commit/91cbcffa68ac1e8391f9c58b70d047ef4d357c49))
* remove SFTP spike ([f866174](https://gitlab.com/bubblehouse/django-moo/commit/f866174d01722996fd908db9a4ffb72c1f7136fc))
* remove shadowed describe verb ([a2871b4](https://gitlab.com/bubblehouse/django-moo/commit/a2871b4cf3a64725f2cc525469a572803b5c0b9c))
* remove some other sandbox escapes ([0dac23a](https://gitlab.com/bubblehouse/django-moo/commit/0dac23af3a0a7b73779dd06198a91bc36c3dd943))
* remove spurious env var ([9d78a8c](https://gitlab.com/bubblehouse/django-moo/commit/9d78a8cc6157f7c6c02d1886210f1a617b0d0263))
* remove unnecessary use of inherit_owner, will restore as needed ([c6185b1](https://gitlab.com/bubblehouse/django-moo/commit/c6185b12ec6858449f89390b1cc3dde0b58169bf))
* remove use of sprintf because of missing `this` ([c0774dd](https://gitlab.com/bubblehouse/django-moo/commit/c0774dd93cc31ca8598c8c3aa88807049eb06d26))
* removed line editor from asyncssh since prompt-toolkit handles lines ([661d867](https://gitlab.com/bubblehouse/django-moo/commit/661d867af42113cb22c4fdb6a5dc6c096d2bd6f2))
* removed need for BLOCKED_IMPORTS ([608e410](https://gitlab.com/bubblehouse/django-moo/commit/608e410029f3c4cd7a919811730de4679216ca68))
* rename functions ([70f1b24](https://gitlab.com/bubblehouse/django-moo/commit/70f1b24f97f5aef04de9ab9f394b49b6087d047b))
* resolve split dev dependency sections and upgrade packages ([b076f21](https://gitlab.com/bubblehouse/django-moo/commit/b076f21d33fac79bfcc55d3902c1744ec7ae83c8))
* restore default bootstrap after mistaking it for test ([06db7cb](https://gitlab.com/bubblehouse/django-moo/commit/06db7cbe7efe8e06d66e342d6899de7bf5a9d53f))
* restore RestrictedPythons list of INSPECT_ATTRIBUTES ([68f1206](https://gitlab.com/bubblehouse/django-moo/commit/68f12064f1ec4d5b395e23a8af8c2eb4520b1ad7))
* revert updates ([ae6e752](https://gitlab.com/bubblehouse/django-moo/commit/ae6e7528878b00545c18c991e2020ba24f35332b))
* rewrap description paragraphs before output ([02c7cad](https://gitlab.com/bubblehouse/django-moo/commit/02c7cad930b07bdede72663f7f304d87cf696865))
* route enterfunc print output to player and fix original_location tracking after move ([b42a231](https://gitlab.com/bubblehouse/django-moo/commit/b42a231456c1444b1c4da63a2aba8a497b90a761))
* run anybadge through uv ([7f91514](https://gitlab.com/bubblehouse/django-moo/commit/7f91514c05ba945d21e8d9979c1bd574392247c3))
* run as www-data at the container level, dont drop permissions ([131c012](https://gitlab.com/bubblehouse/django-moo/commit/131c012ebeedfd780770d4e4851b348185adf604))
* sandbox escape fix for original_owner, original_location ([0e748f8](https://gitlab.com/bubblehouse/django-moo/commit/0e748f88643c93faa57ac4c9ed6c8240d0cbad9b))
* set __file__ when using a file-backed verb ([f299c0f](https://gitlab.com/bubblehouse/django-moo/commit/f299c0f568f0d6b827d26dcf1654fadfdff996e5))
* set correct owner when moving ([a319d20](https://gitlab.com/bubblehouse/django-moo/commit/a319d20462ebbcca31e2fd9a83a28591fa35c712))
* set default dir to /usr/app [ci skip] ([fad59b9](https://gitlab.com/bubblehouse/django-moo/commit/fad59b97c39792ca54f2d6417193431ccf9828b9))
* set default messages for things ([8891d08](https://gitlab.com/bubblehouse/django-moo/commit/8891d08ea3fbec2b284bdcef779a28bd01e293c2))
* set permissions so www-data can use the host key ([c088049](https://gitlab.com/bubblehouse/django-moo/commit/c088049ae06c1202d6a4885c053c0ed8cd54f82e))
* short term fix to ssh hostname issue ([bd949ee](https://gitlab.com/bubblehouse/django-moo/commit/bd949eeaaa9b07e2231db0ccb33f8729ae91ab3a))
* sketching out first verb ([79c8262](https://gitlab.com/bubblehouse/django-moo/commit/79c8262d1f1d401cd9d8b0fb356c197f286c4469))
* sleep before starting server to give time for the previous server port to be closed ([c926a6f](https://gitlab.com/bubblehouse/django-moo/commit/c926a6fd9619ecd6e527458b552486b26061643e))
* small tweaks and debug improvements for verbs ([70f1622](https://gitlab.com/bubblehouse/django-moo/commit/70f1622515894f67265eb91b2ae83e9f1214072c))
* small verb fixes from testing ([3fdef4a](https://gitlab.com/bubblehouse/django-moo/commit/3fdef4a0b763bf8640c3bc6141eacad3b45391ce))
* start using base image ([ba81f04](https://gitlab.com/bubblehouse/django-moo/commit/ba81f04a30de6ba933363660c00e147ef9ec589c))
* starting to implement proper context support ([f1ce9f9](https://gitlab.com/bubblehouse/django-moo/commit/f1ce9f9b85b2f00b9f42471feabe856bd6d7f0c1))
* support creating object in the void ([99d2cf0](https://gitlab.com/bubblehouse/django-moo/commit/99d2cf04f3fd4ac6065acc58d660f54b4d33441c))
* syntax issues with color tags ([64cbe7f](https://gitlab.com/bubblehouse/django-moo/commit/64cbe7ff08d335d4ee52dd0bbb21f7eb2af5284e))
* tests broken by parser changes ([ec4b004](https://gitlab.com/bubblehouse/django-moo/commit/ec4b00405e699e23d96994d89da529aafcc3bd48))
* tests broken by parser changes ([a816c21](https://gitlab.com/bubblehouse/django-moo/commit/a816c218a8696f47b3b0e3b2d057576b31a64707))
* the DB hostname should be overrideable ([8785eb9](https://gitlab.com/bubblehouse/django-moo/commit/8785eb9ae56d2bf94b5af65a58e9f260e2f49b93))
* the default description for an object should be the empty string ([1bfbf97](https://gitlab.com/bubblehouse/django-moo/commit/1bfbf971e3b2382629d7f6a27cae67ef499eab83))
* the real issue was using `command` instead of `args` ([208f0a0](https://gitlab.com/bubblehouse/django-moo/commit/208f0a04e85ed1b8def672d9d988925526d35fa7))
* throw warnings when trying to write without redis ([d0fba9d](https://gitlab.com/bubblehouse/django-moo/commit/d0fba9d7d41a9b749a767adb617c032cdf95909b))
* try inserting python ([421f026](https://gitlab.com/bubblehouse/django-moo/commit/421f02605fe8d73b2322b87f866a726407539f68))
* try removing leading ./ from command ([ffe1528](https://gitlab.com/bubblehouse/django-moo/commit/ffe152883d76379df9836ff31cb6e89871eb74fe))
* try using non-serverless micro DB ([3446ccb](https://gitlab.com/bubblehouse/django-moo/commit/3446ccb8c5f16e2a377d1d967088eb17ce36d01a))
* typo in exception message ([31d973b](https://gitlab.com/bubblehouse/django-moo/commit/31d973bd26c4fd4871f3a6ef70b25bdec06aa00c))
* typo, should be return, not raise ([6927c63](https://gitlab.com/bubblehouse/django-moo/commit/6927c635a1b887176347693c610f2f3e238ccbc9))
* unit test errors ([fba0a9c](https://gitlab.com/bubblehouse/django-moo/commit/fba0a9cd3bb3e0b50179a5ca0780cf56f49edfc6))
* unquote needs to be more intelligent ([09bafb7](https://gitlab.com/bubblehouse/django-moo/commit/09bafb7e723b54cef5bcf6bc982b3397df1ec5c5))
* update base imge ([6afa2ae](https://gitlab.com/bubblehouse/django-moo/commit/6afa2ae88ad2f868a863c011aacfb8c6c480792c))
* update Celery configuration to use external file ([e1df0d1](https://gitlab.com/bubblehouse/django-moo/commit/e1df0d1e368bd2bdcde2e6cb95f7e96b09a2fd57))
* update chart image ([65b4727](https://gitlab.com/bubblehouse/django-moo/commit/65b47272cec7f352cb324dc93a1ca7f8bfbae752))
* update CI packages ([c36ee80](https://gitlab.com/bubblehouse/django-moo/commit/c36ee8046284af625517d1742d7edc503efa2ad5))
* update existing player objects properly when using moo_enableuser ([caab2dd](https://gitlab.com/bubblehouse/django-moo/commit/caab2dd93d547a3b21674c8931c4c2e29addbd7c))
* update runner-base images in CI pipeline ([ade7da6](https://gitlab.com/bubblehouse/django-moo/commit/ade7da6786dfb17dda78a38519606321fd3ccac5))
* update the webssh template directly in the container ([73e94c4](https://gitlab.com/bubblehouse/django-moo/commit/73e94c4ef872aad6e83c944070e13a4b634fae31))
* update the webssh template directly in the container ([b52c817](https://gitlab.com/bubblehouse/django-moo/commit/b52c817c675fb8ae161c67482a19150955353ff6))
* update to db creds on dev ([d0f8237](https://gitlab.com/bubblehouse/django-moo/commit/d0f82378e4996fcaa081e92458cd6902d2433fd0))
* update to python3.11 ([db9b01e](https://gitlab.com/bubblehouse/django-moo/commit/db9b01e8ed865b0a606823c85f1db591f901cb9c))
* update trusted hostname ([c20cdd6](https://gitlab.com/bubblehouse/django-moo/commit/c20cdd6e759d541956fe831a70652504e0e04039))
* update trusted hostname ([37344be](https://gitlab.com/bubblehouse/django-moo/commit/37344beffe202abadda42f2fcd2390d629bc35b3))
* update trusted hostname one last time ([fc8af4c](https://gitlab.com/bubblehouse/django-moo/commit/fc8af4c2655063fe464959bef4ddac1577fc40de))
* updated dependencies ([c912fb3](https://gitlab.com/bubblehouse/django-moo/commit/c912fb3d66e90f0b05a31f0c5b6b24169339aaac))
* updated Dockerfile and entrypoint after uv migration ([e4b5b9e](https://gitlab.com/bubblehouse/django-moo/commit/e4b5b9eee22909330bcaf3ede1e6bd8ac6209079))
* updated lockfile ([6ce8bb0](https://gitlab.com/bubblehouse/django-moo/commit/6ce8bb0e44eacb51fb555b8bd8711481d7c785be))
* updated to Django 5.0 ([e7923a7](https://gitlab.com/bubblehouse/django-moo/commit/e7923a7975e5ba87a0bc54a27dd06a898d1febf4))
* use a known working redis version for dependency ([61cb3f1](https://gitlab.com/bubblehouse/django-moo/commit/61cb3f1c1c4829b8650b9d981417e5a36cd0b3ab))
* use a single eval function for both ([ae6747e](https://gitlab.com/bubblehouse/django-moo/commit/ae6747eae6cb4e4d063574bf9f17a2357e20fbbc))
* use correct arch when installing uv ([d66a086](https://gitlab.com/bubblehouse/django-moo/commit/d66a086bb68c9d49b9b185da1405ab980dbd26cd))
* use correct args in helm chart ([d69e24e](https://gitlab.com/bubblehouse/django-moo/commit/d69e24e170e8f988870e56d55903e0efb0fe9d5a))
* use correct listening address ([9e60b6c](https://gitlab.com/bubblehouse/django-moo/commit/9e60b6caec1e46a65e9d7f077d4f73f2150691d8))
* use correct OCI path ([78cf39b](https://gitlab.com/bubblehouse/django-moo/commit/78cf39b8947734fcd4d6e5d695d4994c867106a0))
* use correct package url ([bba4862](https://gitlab.com/bubblehouse/django-moo/commit/bba4862b48357f6a82955445fc8878aff464994d))
* use correct PK for system ([801fc94](https://gitlab.com/bubblehouse/django-moo/commit/801fc9400e8b5fa1a4b30b3c350e2bd162617a72))
* use correct server url ([0b1198b](https://gitlab.com/bubblehouse/django-moo/commit/0b1198b2dc8dd47864b40bfb9dc7bb6194de1133))
* use english_list in tell_contents ([ca40124](https://gitlab.com/bubblehouse/django-moo/commit/ca40124ec48368ec2840f5a1ed4040c183715b66))
* use existing hosts ([059f291](https://gitlab.com/bubblehouse/django-moo/commit/059f291feea34057b1e70c479f8dba6afcb27504))
* use latest version with correct OCI path ([b402a12](https://gitlab.com/bubblehouse/django-moo/commit/b402a12071ab4a3658a8de42fe7eb3c9fa5a6652))
* use moo de-serialization for property values ([f5e55a5](https://gitlab.com/bubblehouse/django-moo/commit/f5e55a513acca2d3a3c5c07ff033c0056112c49c))
* use player, not caller ([2651103](https://gitlab.com/bubblehouse/django-moo/commit/2651103f01af6e069f494258d29c0702fc93a4d1))
* use poetry publish ([113008a](https://gitlab.com/bubblehouse/django-moo/commit/113008ac2813e5d7a35f0b6579f5b64180dd1c0b))
* use port name ([d12f32c](https://gitlab.com/bubblehouse/django-moo/commit/d12f32c57ec594496c24948d43a44c736042d305))
* use same redis client in dev as other envs ([e0ec0a3](https://gitlab.com/bubblehouse/django-moo/commit/e0ec0a337478180677dfad6247a486bfb31e9b46))
* use signals instead of overriding through.save() ([617dca0](https://gitlab.com/bubblehouse/django-moo/commit/617dca0ddf5b7ed64ae37b51e9b1f46a9e523b6b))
* use tell in reload for status messages ([0d22b77](https://gitlab.com/bubblehouse/django-moo/commit/0d22b7733b02bb56d8aca979463345339a44b259))
* use tell in reload for status messages ([8de394a](https://gitlab.com/bubblehouse/django-moo/commit/8de394a2a75e350b43af1aa8c64dde24400650d6))
* use the correct redis host in dev ([0514e43](https://gitlab.com/bubblehouse/django-moo/commit/0514e432d3020915b5b5673c76725eaf935ad24f))
* use warnings instead of logging them ([b799474](https://gitlab.com/bubblehouse/django-moo/commit/b79947487bf6796247eaac76f7dcdf70977c5868))
* uwsgi path fix ([df34408](https://gitlab.com/bubblehouse/django-moo/commit/df3440847f89a9e0a2c98ac89caa3199a66fafc3))
* uwsgi platform fix ([da08684](https://gitlab.com/bubblehouse/django-moo/commit/da08684e5c5c2551478ee036a74b4f36ff082642))
* verb cleanup ([0119227](https://gitlab.com/bubblehouse/django-moo/commit/01192275fee8d98255e4711b7657ae877390d5a3))
* verb environment globals ([0225ce0](https://gitlab.com/bubblehouse/django-moo/commit/0225ce080683f2db11877ec34756305738818dba))
* vscode configuration, sandbox escapes ([bddb1e3](https://gitlab.com/bubblehouse/django-moo/commit/bddb1e3de69c6198a014945e3ab62074666a37b0))
* webapp port clobbered ([46fe901](https://gitlab.com/bubblehouse/django-moo/commit/46fe90115bae9380d73d61c463ff160028cb217b))
* webssh deployment to helm chart ([2fd6a50](https://gitlab.com/bubblehouse/django-moo/commit/2fd6a508eb5a384e39191059ab9b705c3d0d1c45))
* yet more sandbox escapes ([87c52dd](https://gitlab.com/bubblehouse/django-moo/commit/87c52dd2a26225e77e6fb18025c10d624c19eed4))

## [0.89.1](https://gitlab.com/bubblehouse/django-moo/compare/v0.89.0...v0.89.1) (2026-03-28)

### Bug Fixes

* dont print tracebacks for UserErrors, even to wizards ([b816055](https://gitlab.com/bubblehouse/django-moo/commit/b8160559e7a15a3265fe06e555909b460d95fc51))
* properly display the first output (look_self) ([0dba75e](https://gitlab.com/bubblehouse/django-moo/commit/0dba75e771ae2748abf87aa618b0772d2fbb3b38))

## [0.89.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.88.3...v0.89.0) (2026-03-28)

### Features

* added ; shortcut for [@eval](https://gitlab.com/eval) ([449036e](https://gitlab.com/bubblehouse/django-moo/commit/449036ed398c1be45a7138da30063b43150c1bac))
* added $do_command support, closes [#7](https://gitlab.com/bubblehouse/django-moo/issues/7) ([fee1d87](https://gitlab.com/bubblehouse/django-moo/commit/fee1d8741d9dc8e3b1eb36aa85031b868f8efb41))
* implemented OUTPUTPREFIX, OUTPUTSUFFIX and .flush. closes [#6](https://gitlab.com/bubblehouse/django-moo/issues/6) ([0984956](https://gitlab.com/bubblehouse/django-moo/commit/09849563630073056a2ab59512146c309d01b0df))

### Bug Fixes

* pre-import moo.sdk.* when running [@eval](https://gitlab.com/eval) ([21f2110](https://gitlab.com/bubblehouse/django-moo/commit/21f21108f173206868894d049174148c9fe6fbb0))

## [0.88.3](https://gitlab.com/bubblehouse/django-moo/compare/v0.88.2...v0.88.3) (2026-03-28)

### Bug Fixes

* rewrap description paragraphs before output ([dcabc59](https://gitlab.com/bubblehouse/django-moo/commit/dcabc59519e9331dd1da4d6ce82c74c504cf15c9))

## [0.88.2](https://gitlab.com/bubblehouse/django-moo/compare/v0.88.1...v0.88.2) (2026-03-27)

### Bug Fixes

* call confunc and disfunc properly ([25065fe](https://gitlab.com/bubblehouse/django-moo/commit/25065fe15f2364ec0c276a24e392a5bd8c48efa4))

## [0.88.1](https://gitlab.com/bubblehouse/django-moo/compare/v0.88.0...v0.88.1) (2026-03-27)

### Bug Fixes

* missing arg in signup method ([669c4cd](https://gitlab.com/bubblehouse/django-moo/commit/669c4cd08006635443a54a970d8bb970a474b53b))
* registration style and flow issues ([e7de85d](https://gitlab.com/bubblehouse/django-moo/commit/e7de85d7301fdac2ec65e03c3b7fc94ce964cc6b))

## [0.88.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.87.0...v0.88.0) (2026-03-25)

### Features

* added registration flow with django-allauth ([d8ee00a](https://gitlab.com/bubblehouse/django-moo/commit/d8ee00a3c026982bedcad01daa1a6fa9196b4317))

## [0.87.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.86.0...v0.87.0) (2026-03-24)

### Features

* merged webssh index.html into django for foture expansion ([c6ab176](https://gitlab.com/bubblehouse/django-moo/commit/c6ab176abe00f28c5fdf4c16d8b0b5dfc807fff1))

## [0.86.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.85.1...v0.86.0) (2026-03-24)

### Features

* added verbs to enable ssh key management ([8451899](https://gitlab.com/bubblehouse/django-moo/commit/845189929a0b58d98758833c5b89feb4b95ffc96))
* added verbs to enable ssh key management ([96be4d7](https://gitlab.com/bubblehouse/django-moo/commit/96be4d7a8b0a6bdb11389235c9211931dd2f9756))

## [0.85.1](https://gitlab.com/bubblehouse/django-moo/compare/v0.85.0...v0.85.1) (2026-03-21)

### Bug Fixes

* interchangeable prepositions are now working ([f35697c](https://gitlab.com/bubblehouse/django-moo/commit/f35697c82815bb2be65080365658115af306ae8d))

## [0.85.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.84.0...v0.85.0) (2026-03-21)

### Features

* support editor use with describe ([459051e](https://gitlab.com/bubblehouse/django-moo/commit/459051e64100de7bb03c20577341ce46f4ecc3b4))

## [0.84.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.83.0...v0.84.0) (2026-03-21)

### Features

* added $furniture class for immovable sittable objects ([6122691](https://gitlab.com/bubblehouse/django-moo/commit/612269159caedd863a899972fb44b920da1027cc))

## [0.83.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.82.0...v0.83.0) (2026-03-21)

### Features

* added boot_player() and implemented true [@quit](https://gitlab.com/quit) verb ([66b0eb7](https://gitlab.com/bubblehouse/django-moo/commit/66b0eb7607875f443eb4ef3015929671fbb964c4))
* support `obvious` on objects ([7fcc694](https://gitlab.com/bubblehouse/django-moo/commit/7fcc6945d1a3969d2ce0d51b3080af42bffbcf2e))

### Bug Fixes

* correct escaping in at_describe ([67f20bf](https://gitlab.com/bubblehouse/django-moo/commit/67f20bfaf22ff3799d2a80bf0b814a5c8bab185f))
* further ssh improvements ([854edf9](https://gitlab.com/bubblehouse/django-moo/commit/854edf96d1efeb8ad74ae860e01a444e5ffc2f30))
* improve verb write handling ([5233cec](https://gitlab.com/bubblehouse/django-moo/commit/5233cec2aa23886dd1c83b8d7b5ae3b8f2eeaa7c))
* linting errors ([0305f75](https://gitlab.com/bubblehouse/django-moo/commit/0305f759dba5cbc945dd5b98d66482d6ab5dfda1))
* typo, should be return, not raise ([189cb11](https://gitlab.com/bubblehouse/django-moo/commit/189cb11dd4b71bd29f104a70b143b9b12f9130e5))
* unquote needs to be more intelligent ([9ff07ed](https://gitlab.com/bubblehouse/django-moo/commit/9ff07edc249961221db4a4221202b1eae50e8fb9))

## [0.82.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.81.3...v0.82.0) (2026-03-20)

### Features

* added [@alias](https://gitlab.com/alias) function for all players ([9359109](https://gitlab.com/bubblehouse/django-moo/commit/9359109abfc6271fb174c84864d6fd6322bb53f8))
* added [@eval](https://gitlab.com/eval) verb for $programmers ([11d8776](https://gitlab.com/bubblehouse/django-moo/commit/11d8776fd50d8bc1afb6545c25f938ec6ecf4b6f))
* added `random` to sandbox imports ([d2512ad](https://gitlab.com/bubblehouse/django-moo/commit/d2512ad02b5a8112121a72ae30558fd9f8208be0))
* added more invocation styles for [@edit](https://gitlab.com/edit) ([41af63e](https://gitlab.com/bubblehouse/django-moo/commit/41af63e94c712acf89178d67d23696b40ed6cdf4))
* added PREFIX/SUFFIX/QUIET verbs to manage client connection features ([c27300f](https://gitlab.com/bubblehouse/django-moo/commit/c27300fe6d84224f410f53e7a0dd7520287aa001))
* let specifying verbs and props at the CLI with [@edit](https://gitlab.com/edit) ([bc84963](https://gitlab.com/bubblehouse/django-moo/commit/bc849635546a6beeec4c4e1b949c996426e25209))

### Bug Fixes

* support creating object in the void ([b61b81f](https://gitlab.com/bubblehouse/django-moo/commit/b61b81fb91e0f063c0f9074537310c2c1ba19794))

## [0.81.3](https://gitlab.com/bubblehouse/django-moo/compare/v0.81.2...v0.81.3) (2026-03-18)

### Bug Fixes

* add black to dependencies and update agent docs ([a32d643](https://gitlab.com/bubblehouse/django-moo/commit/a32d643e82ef296eb049acc8c787b07f77eb67c3))

## [0.81.2](https://gitlab.com/bubblehouse/django-moo/compare/v0.81.1...v0.81.2) (2026-03-18)

### Bug Fixes

* added DjangoMOO to page title ([bb35496](https://gitlab.com/bubblehouse/django-moo/commit/bb35496f95ecae755a2ee532a1947c8834f4bac5))
* improve title of editor ([6c02012](https://gitlab.com/bubblehouse/django-moo/commit/6c02012041d48127a7e7cf1b8b6c0aec8672cfa1))
* lookup() should understand pronouns ([4ed0249](https://gitlab.com/bubblehouse/django-moo/commit/4ed02491f16518a144956d51ee78cc7f0fa0af6d))

## [0.81.1](https://gitlab.com/bubblehouse/django-moo/compare/v0.81.0...v0.81.1) (2026-03-18)

### Bug Fixes

* acl __str__ verb refs ([84e7809](https://gitlab.com/bubblehouse/django-moo/commit/84e78090ee4053c4b412e83e5967aca1a97042d1))
* remove shadowed describe verb ([f5fb74b](https://gitlab.com/bubblehouse/django-moo/commit/f5fb74bd85fbc31e12f95076c6dfde37b82c793d))

## [0.81.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.80.4...v0.81.0) (2026-03-17)

### Features

* added context.task_time object to help write verbs that last longer than the timeout ([d1a2d0a](https://gitlab.com/bubblehouse/django-moo/commit/d1a2d0a8a1d2449d0668383a41f0c2fa6b78641d))

## [0.80.4](https://gitlab.com/bubblehouse/django-moo/compare/v0.80.3...v0.80.4) (2026-03-17)

### Bug Fixes

* possessive noun lookup IndexError in Parser.find_object ([41b32da](https://gitlab.com/bubblehouse/django-moo/commit/41b32dade07448da8c8ce9a2397baf3b7845ffe9))

## [0.80.3](https://gitlab.com/bubblehouse/django-moo/compare/v0.80.2...v0.80.3) (2026-03-17)

### Bug Fixes

* install django-extensions for debug purposes ([e730e9b](https://gitlab.com/bubblehouse/django-moo/commit/e730e9b8c89b0fc2fc26dfa6521adada4c3a854f))
* install django-extensions for debug purposes ([b7683eb](https://gitlab.com/bubblehouse/django-moo/commit/b7683eb817611983c594584408d68cc2b10490bd))
* restore RestrictedPythons list of INSPECT_ATTRIBUTES ([b00ca8d](https://gitlab.com/bubblehouse/django-moo/commit/b00ca8d0328cb749cfabaa8c92ef037c3197aa0d))

## [0.80.2](https://gitlab.com/bubblehouse/django-moo/compare/v0.80.1...v0.80.2) (2026-03-16)

### Bug Fixes

* frame access exploit and str.format issue, block modules ([3927933](https://gitlab.com/bubblehouse/django-moo/commit/3927933407c48b8eb60ad18707670d219a94ac58))
* install django-extensions for debug purposes ([be06b50](https://gitlab.com/bubblehouse/django-moo/commit/be06b50c909c100250beffa0742e68971986f7af))
* removed need for BLOCKED_IMPORTS ([6412b9f](https://gitlab.com/bubblehouse/django-moo/commit/6412b9f959bc1688e0d1a21a60a123e6ffb2aca8))
* use tell in reload for status messages ([5ee6a6a](https://gitlab.com/bubblehouse/django-moo/commit/5ee6a6affdd0aa1161b94adfcf6898200946f102))
* use tell in reload for status messages ([1192c60](https://gitlab.com/bubblehouse/django-moo/commit/1192c604d7cad6985242abf4c74cd3c9fad831e6))

## [0.80.1](https://gitlab.com/bubblehouse/django-moo/compare/v0.80.0...v0.80.1) (2026-03-15)

### Bug Fixes

* short term fix to ssh hostname issue ([c95788c](https://gitlab.com/bubblehouse/django-moo/commit/c95788c9af2bfa384ef2455ca0d362760f1b95c3))

## [0.80.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.79.2...v0.80.0) (2026-03-15)

### Features

* added additional syntaxes to [@reload](https://gitlab.com/reload) ([adc7c26](https://gitlab.com/bubblehouse/django-moo/commit/adc7c26ee5e275c03a986a6a7b41f4ca191b2653))

## [0.79.2](https://gitlab.com/bubblehouse/django-moo/compare/v0.79.1...v0.79.2) (2026-03-15)

### Bug Fixes

* uwsgi path fix ([bb4d468](https://gitlab.com/bubblehouse/django-moo/commit/bb4d468c61480445971115696d0675822eda1ff0))

## [0.79.1](https://gitlab.com/bubblehouse/django-moo/compare/v0.79.0...v0.79.1) (2026-03-15)

### Bug Fixes

* more sandbox escapes ([083df3b](https://gitlab.com/bubblehouse/django-moo/commit/083df3b67cd079d0292d5fd5bbf3ec4db1f7a5e4))
* sandbox escape fix for original_owner, original_location ([e21162b](https://gitlab.com/bubblehouse/django-moo/commit/e21162b518df1bbcbef1798348864a45c9b7159e))
* vscode configuration, sandbox escapes ([96a055b](https://gitlab.com/bubblehouse/django-moo/commit/96a055b22ed5792192b60b2519d94bde4dce45b1))
* yet more sandbox escapes ([5387270](https://gitlab.com/bubblehouse/django-moo/commit/5387270b86734415168d68eb498bb8538968c9c8))

## [0.79.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.78.1...v0.79.0) (2026-03-15)

### Features

* refactor moo.core into moo.sdk for verb isolation purposes ([908831a](https://gitlab.com/bubblehouse/django-moo/commit/908831a9720f7501ab494af9e1c77a8e47c87e5b))

### Bug Fixes

* more sandbox escapes, removed some superflous tests ([ed7e25e](https://gitlab.com/bubblehouse/django-moo/commit/ed7e25e126c884fa681008a82fd631995616c6f2))

## [0.78.1](https://gitlab.com/bubblehouse/django-moo/compare/v0.78.0...v0.78.1) (2026-03-14)

### Bug Fixes

* force release ([a7bfa48](https://gitlab.com/bubblehouse/django-moo/commit/a7bfa485f4fff2e055943ab39ccb4fb7998d920f))

## [0.78.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.77.4...v0.78.0) (2026-03-14)

### Features

* use correct hostname in webssh when deployed ([ee3b9ad](https://gitlab.com/bubblehouse/django-moo/commit/ee3b9ad00bd69c92cd5e6b1d297c103ec7e72a5a))

## [0.77.4](https://gitlab.com/bubblehouse/django-moo/compare/v0.77.3...v0.77.4) (2026-03-14)

### Bug Fixes

* don't use parallel cmake builds if you like your homelab ([b6bc052](https://gitlab.com/bubblehouse/django-moo/commit/b6bc0526bc3a9de5745f8a7b9da4b5ad2de5a8f5))
* enable post-quantum key exchange in SSH server ([8a11104](https://gitlab.com/bubblehouse/django-moo/commit/8a111042bd3053526f9b2bfca650b7665a7bfb5c))
* extend job timeout ([592d679](https://gitlab.com/bubblehouse/django-moo/commit/592d679f4915cfb557f604f1f3c7ddb880792426))
* many sandbox escape vectors identified and sealed ([d73786a](https://gitlab.com/bubblehouse/django-moo/commit/d73786a3195badcc178195831d44a114dd4fda74))
* more sandbox escapes for ORM ([d8f6311](https://gitlab.com/bubblehouse/django-moo/commit/d8f6311b06226004623fc0771497856bada607fe))
* remove some other sandbox escapes ([3d50323](https://gitlab.com/bubblehouse/django-moo/commit/3d50323fbe1e78bca3d57f728cc1fdfc735ffde0))
* set default dir to /usr/app [ci skip] ([364c315](https://gitlab.com/bubblehouse/django-moo/commit/364c3155518e51129ef1d0cd722147efb1fad42c))
* uwsgi platform fix ([d7e9ff6](https://gitlab.com/bubblehouse/django-moo/commit/d7e9ff6d604db72d477bdf26dc73797163907254))

## [0.77.3](https://gitlab.com/bubblehouse/django-moo/compare/v0.77.2...v0.77.3) (2026-03-13)

### Bug Fixes

* enable post-quantum key exchange in SSH server ([ddc945b](https://gitlab.com/bubblehouse/django-moo/commit/ddc945be3452cb1958b50da7a7e1cd69c6df64cb))

## [0.77.2](https://gitlab.com/bubblehouse/django-moo/compare/v0.77.1...v0.77.2) (2026-03-13)

### Bug Fixes

* force release ([2076afb](https://gitlab.com/bubblehouse/django-moo/commit/2076afb933bef50e29b7dde7e858a6c7c1d9e8b4))

## [0.77.1](https://gitlab.com/bubblehouse/django-moo/compare/v0.77.0...v0.77.1) (2026-03-13)

### Bug Fixes

* the DB hostname should be overrideable ([71f24de](https://gitlab.com/bubblehouse/django-moo/commit/71f24de902710af88af59086bc20bc3f7b4cbea9))

## [0.77.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.76.0...v0.77.0) (2026-03-13)

### Features

* added support for postgresql subchart ([82fd19d](https://gitlab.com/bubblehouse/django-moo/commit/82fd19dae254406af2ba3958e9a5f7ff744b3416))

## [0.76.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.75.0...v0.76.0) (2026-03-13)

### Features

* replace Django model exceptions with custom ones that are formatted by the parser task ([5c2f384](https://gitlab.com/bubblehouse/django-moo/commit/5c2f384d871d8253d8d50ccf2b6baad4a18b9eed))
* use the redis result backend when not in testing ([5404537](https://gitlab.com/bubblehouse/django-moo/commit/5404537de7c567a5d08925e8ccb471b295abcc3e))

## [0.75.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.74.0...v0.75.0) (2026-03-13)

### Features

* prompt shortcuts, like " to trigger say "" ([f5960d9](https://gitlab.com/bubblehouse/django-moo/commit/f5960d9dfdf2c3b5e979fa7aab811232e1c2251a))

## [0.74.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.73.0...v0.74.0) (2026-03-12)

### Features

* added remaining room functions ([857feb4](https://gitlab.com/bubblehouse/django-moo/commit/857feb4b198ff8b018c3925130415c20290e3036))
* created players() primitive and parser.get_search_order() ([1c28792](https://gitlab.com/bubblehouse/django-moo/commit/1c287926e7179040248f9df6d10f126617ea9ff0))

## [0.73.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.72.0...v0.73.0) (2026-03-12)

### Features

* added last_connection_time property, connected_users() helper function, and use it in look_self on the player object ([413b8b5](https://gitlab.com/bubblehouse/django-moo/commit/413b8b5e7761651d3fd4da8596d4820d4dbfc97c))

## [0.72.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.71.0...v0.72.0) (2026-03-12)

### Features

* replace custom pager with pypager ([c6f1311](https://gitlab.com/bubblehouse/django-moo/commit/c6f1311a6c8d8ecdeaf77fe6217995026f72df3d))

## [0.71.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.70.0...v0.71.0) (2026-03-12)

### Features

* added paginator support to [@show](https://gitlab.com/show) to show verbs and properties ([5f361b7](https://gitlab.com/bubblehouse/django-moo/commit/5f361b7f45df378016391047367f016089d6ed90))

## [0.70.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.69.0...v0.70.0) (2026-03-12)

### Features

* added open_paginator client function ([4cfc1f7](https://gitlab.com/bubblehouse/django-moo/commit/4cfc1f70caa1ed5ae8afa952246ae77329adcb92))

### Bug Fixes

* handle prompt when user is nowhere ([3100626](https://gitlab.com/bubblehouse/django-moo/commit/3100626c3ca5c6090a8a5c084e7383c84b1e2b6f))

## [0.69.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.68.0...v0.69.0) (2026-03-12)

### Features

* added $note and $letter classes ([72bad62](https://gitlab.com/bubblehouse/django-moo/commit/72bad6225e4d5e494bf853b5b54921d9c59b51b8))

## [0.68.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.67.3...v0.68.0) (2026-03-11)

### Features

* use solarized-dark for the code editor ([7c5e230](https://gitlab.com/bubblehouse/django-moo/commit/7c5e230f49cabf1a9be9ffed18166c88203ff478))

## [0.67.3](https://gitlab.com/bubblehouse/django-moo/compare/v0.67.2...v0.67.3) (2026-03-11)

### Bug Fixes

* move player setup into dataset_initialize ([46ad48a](https://gitlab.com/bubblehouse/django-moo/commit/46ad48ab0fc12de2ba5e32215bc81e0598eda3f1))
* parser bugs for unusual situations ([5ff9df9](https://gitlab.com/bubblehouse/django-moo/commit/5ff9df91a2203e8df9eaf8c73fdb0358dae3e4f2))

## [0.67.2](https://gitlab.com/bubblehouse/django-moo/compare/v0.67.1...v0.67.2) (2026-03-11)

### Bug Fixes

* improve exception handling by parser ([002d390](https://gitlab.com/bubblehouse/django-moo/commit/002d3907e29b176630b37d2f9bb3732891b4e3db))

## [0.67.1](https://gitlab.com/bubblehouse/django-moo/compare/v0.67.0...v0.67.1) (2026-03-11)

### Bug Fixes

* add default OTEL_SERVICE_NAME to chart ([177a9d3](https://gitlab.com/bubblehouse/django-moo/commit/177a9d358a075e4b94ffaed2df26e26173aa2be7))

## [0.67.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.66.0...v0.67.0) (2026-03-11)

### Features

* removed unused Task model ([205ae5e](https://gitlab.com/bubblehouse/django-moo/commit/205ae5eb4c2575c3cf4435849079cb5dd75e614c))

### Bug Fixes

* incorrect is_bound() handling ([a02f759](https://gitlab.com/bubblehouse/django-moo/commit/a02f7592973068d8ecb1ccb3e3059fe15af270fd))

## [0.66.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.65.8...v0.66.0) (2026-03-11)

### Features

* add simple text editor feature that can be used by wizard verbs ([88a514a](https://gitlab.com/bubblehouse/django-moo/commit/88a514a7f075a628248d3f453ccdecdbf75e41c3))
* added [@edit](https://gitlab.com/edit) verb to default_verbs ([6171691](https://gitlab.com/bubblehouse/django-moo/commit/6171691d39b916335fb0615c2cd96a304f5f0956))

### Bug Fixes

* added additional args to callback ([02cb20e](https://gitlab.com/bubblehouse/django-moo/commit/02cb20eb757ea1979bc438685e8468ae247a367a))
* removed line editor from asyncssh since prompt-toolkit handles lines ([54b7d73](https://gitlab.com/bubblehouse/django-moo/commit/54b7d737ace16360e7868c2fb6baa7f70664e47f))

## [0.65](https://gitlab.com/bubblehouse/django-moo/compare/v0.64.0...v0.65.8) (2026-03-09)

### Features

* denormalize ancestor lookups, add cross-session property cache, batch verb dispatch (opt-in) (70475c6)
* further optimizations for quick wins, missing indexes (4e47ccb)

### Bug Fixes

* redis typo (201ef34)
* syntax issues with color tags (6a4ee54)
* handle uncaught test warnings (61abc29)
* route enterfunc print output to player and fix original_location tracking after move (5a560fb)
* preserve player context when invoking verbs asynchronously (ed429ca)
* additional caching and go improvements (10efa56)
* use correct server url (3b3821d)
* use same redis client in dev as other envs (cc1cc51)
* enable batch verb dispatch (28f3125)
* index name too long (b0a9b1d)
* mangled env fix, ci update (64a1368)

## [0.64](https://gitlab.com/bubblehouse/django-moo/compare/v0.63.0...v0.64.0) (2026-03-09)

### Features

* optimized default_verbs to reduce DB calls, introduced better exceptions for verbs (7b8767a)

## [0.63](https://gitlab.com/bubblehouse/django-moo/compare/v0.62.0...v0.63.0) (2026-03-09)

### Features

* convert set_default_permissions to a special case, other verb execution optimizations (98d24f4)

## [0.62](https://gitlab.com/bubblehouse/django-moo/compare/v0.61.2...v0.62.0) (2026-03-09)

### Features

* cache permission tables in the context (a63cca6)
* permission caching improvements and updated indexes (ddd7466)

## [0.61](https://gitlab.com/bubblehouse/django-moo/compare/v0.60.0...v0.61.2) (2026-03-09)

### Features

* time limit is overrideable by env var (d102bd4)

### Bug Fixes

* commit to force release (bf5145b)
* try using non-serverless micro DB (9eaf8b8)
* added admin panel for Relationship for spurious reason that might never happen again (64b3e0b)

## [0.60](https://gitlab.com/bubblehouse/django-moo/compare/v0.59.0...v0.60.0) (2026-03-08)

### Features

* replace O(depth^2) Python recursion in object.py with recursive CTEs; correct parent ordering (5364721)

## [0.59](https://gitlab.com/bubblehouse/django-moo/compare/v0.58.10...v0.59.0) (2026-03-08)

### Features

* lots of DB optimizations for related objects (5ae1bf0)

## [0.58](https://gitlab.com/bubblehouse/django-moo/compare/v0.57.8...v0.58.10) (2026-03-08)

### Features

* use S3 for static assets (5f31fc4)

### Bug Fixes

* added missing django-compressor dependency (151396e)
* installed boto3 (c166221)
* added missing django-storages dependency (866bf66)
* force release (d098be2)
* revert updates (0d5aed5)
* readiness typo (598620b)
* use the correct redis host in dev (4df4f56)
* use correct OCI path (04d0bb9)
* include subchart (ab15ff8)
* added correct redis_cache package (2cce380)
* added missing params for helm push (c2b9b06)
* update base imge (8e9a543)
* update CI packages (bf7f53c)
* update runner-base images in CI pipeline (816bad0)
* use correct package url (dd2e558)
* added missing setting (42dbcb0)
* added redis_cache dependency, setup caches in dev (8ed61f0)

## [0.57](https://gitlab.com/bubblehouse/django-moo/compare/v0.56.4...v0.57.8) (2026-03-07)

### Features

* add redis as a chart dependency (4832e3d)

### Bug Fixes

* the real issue was using `command` instead of `args` (0621b3d)
* try inserting python (c2c4dc7)
* try removing leading ./ from command (064b2da)
* remove spurious env var (eb089e5)
* change migration and collectstatic to pre-hooks (e7caff3)
* update to db creds on dev (1e513e6)
* use latest version with correct OCI path (5e15850)
* use a known working redis version for dependency (acf6b14)

## [0.56](https://gitlab.com/bubblehouse/django-moo/compare/v0.55.0...v0.56.4) (2026-03-07)

### Features

* provide readiness and liveness files (7983595)
* update helm chart with missing components (4e48cd2)

### Bug Fixes

* run as www-data at the container level, dont drop permissions (fdb64dc)
* dont use /var/run (fae2a12)
* use correct args in helm chart (c128bee)
* dont use /var/run (eed24ad)

## [0.55](https://gitlab.com/bubblehouse/django-moo/compare/v0.54.0...v0.55.0) (2026-03-06)

### Features

* added lookup boolean to parser methods (ec2b356)

### Bug Fixes

* update Celery configuration to use external file (9cc5742)

## [0.54](https://gitlab.com/bubblehouse/django-moo/compare/v0.53.0...v0.54.0) (2026-03-06)

### Features

* added [@reload](https://gitlab.com/reload) verb to update filesystem-resident verbs in the database (3e7f8e6)

### Bug Fixes

* resolve split dev dependency sections and upgrade packages (65bf181)

## [0.53](https://gitlab.com/bubblehouse/django-moo/compare/v0.52.2...v0.53.0) (2026-03-04)

### Features

* lookup support $var syntax (59c0619)

### Bug Fixes

* dont include self in tell_contents() (82b216e)
* handle unallocated users in write() (b8c8257)
* update existing player objects properly when using moo_enableuser (a15f76b)

## [0.52](https://gitlab.com/bubblehouse/django-moo/compare/v0.51.0...v0.52.2) (2026-03-04)

### Features

* added $sprintf alias for easy access to the `pronoun_sub` verb (497b2ed)
* added many verbs for $player (f09eacd)
* added more verbs for $player (0f375e0)
* added more verbs for $player (4f85f79)
* added more verbs for $player (44130f8)
* implemented context.caller_stack to see the list of callers (7ad7be4)
* write() and set_task_perms() can ony be called by Wizard-owned code (36f7db9)

### Bug Fixes

* ensure all verbs will be bound before execution, raise exception otherwise (4bfe898)
* fixed remaining caller_stack issues (78d35e9)
* issues in take/get for player (361d924)
* many fixes for player commands (ceb6442)
* remove use of sprintf because of missing `this` (aab6a83)
* unit test errors (3fbeff3)
* exits shouldn't be literally inside the rooms they connect to (630bb05)
* only generic exits should be in location None, objects used as doors should not be moved (cfb473b)
* added stub obj.is_connected() for later implementation (343232e)
* small verb fixes from testing (9aac98a)

## [0.51](https://gitlab.com/bubblehouse/django-moo/compare/v0.50.0...v0.51.0) (2026-02-26)

### Features

* added $gender_utils and tests (4ef8f8f)

### Bug Fixes

* propertly handle "dark" rooms (3c227e2)

## [0.50](https://gitlab.com/bubblehouse/django-moo/compare/v0.49.0...v0.50.0) (2026-02-26)

### Features

* added $string_utils and tests (8df685a)

### Bug Fixes

* parser token should be set to none in every context (e51a0f7)

## [0.49](https://gitlab.com/bubblehouse/django-moo/compare/v0.48.3...v0.49.0) (2026-02-26)

### Features

* renamed the `api` context variable to just `context` for clarity (e946aaf)

## [0.48](https://gitlab.com/bubblehouse/django-moo/compare/v0.47.5...v0.48.3) (2026-02-25)

### Features

* added improved handling of multple prepositions (de58915)
* implementing container support (8116fc2)

### Bug Fixes

* linting issues (cb2857a)
* allow use of the type() builtin (951cb7f)
* handle RESERVED_NAMES properly (9dc3acc)
* moveto has no underscore (3dcdc58)
* the default description for an object should be the empty string (75f9f3e)
* added trivial implementation of $room.tell_contents for now (6077ce6)
* fixed remaining test issues (89a74c5)
* missing f-string prefix (66ae8ff)
* issues found while unit testing, merge old room integration test into new file (2e134b9)

## [0.47](https://gitlab.com/bubblehouse/django-moo/compare/v0.46.2...v0.47.5) (2026-02-23)

### Features

* added remaining room functions (5ffddba)
* added remaining root_class functions, ensure all objects use $root_class if it exists (5b7af13)

### Bug Fixes

* fixes found during testing (e5fb790)
* parser.find_object() searches the player inventory first, then the current location (ff08ce5)
* remove unnecessary use of inherit_owner, will restore as needed (b81f6cf)
* set correct owner when moving (16259c6)
* set default messages for things (fa3653b)
* install uv (4ac9052)
* install uv (fc55505)
* run anybadge through uv (96be7f9)
* updated Dockerfile and entrypoint after uv migration (ef2a771)
* use correct arch when installing uv (0ab45c7)
* --on is required in the moo shebang line (00fa31e)
* added migration to remove old proxy objects, renamed inherited to inherit_owner, other leftover (f8e157d)
* disable Redis in unit tests to avoid blocking issues (383ed3c)
* optimize is_allowed (4e7089b)
* match_object improvements (a435c9d)
* moved look to room, parser now calls huh on failure (1aae1cf)
* prevent Verbs from being called by the admin template engine (0f625a5)
* update the webssh template directly in the container (b8ae502)
* update the webssh template directly in the container (0554075)

## [0.46](https://gitlab.com/bubblehouse/django-moo/compare/v0.45.1...v0.46.2) (2026-02-10)

### Features

* add webssh deployment to helm chart (f314d3c)

### Bug Fixes

* webapp port clobbered (7ac881f)
* webssh deployment to helm chart (aa68c03)

## [0.45](https://gitlab.com/bubblehouse/django-moo/compare/v0.44.3...v0.45.1) (2026-02-02)

### Features

* removed Accessible- proxy objects (1ad9f2d)

### Bug Fixes

* use player, not caller (63e2285)

## [0.44](https://gitlab.com/bubblehouse/django-moo/compare/v0.43.0...v0.44.3) (2026-02-01)

### Features

* added API descriptor value for the Celery task_id (a1daf41)
* added key support and parsing, modify tests to use variable PKs (6b6ecaf)
* implement add_entrance and add_exit, convert dig and tunnel to use those (4f4d1ee)
* implemented support verbs for exits (adf7100)

### Bug Fixes

* almost removed AccessibleObject model (9ac2304)
* create use objects by default so Wizard group rights work (1cd9fb4)
* ensure we always get an accessible object here (c1c1640)
* handle encoding consistently (406a0d7)
* major permissions fixes by adding player (which is static) vs caller (which can change) (bad1836)
* make exceptions available through moo.core (c055dcf)
* moved getattr override to main Object model (09ec6c1)
* properly handle set_task_perms (5967b94)
* properties are not readable by default (d193084)
* properties are not readable by default (fb047d7)
* reimplementing exits (626f06e)
* reimplementing exits (e5a25c9)
* update trusted hostname (9d52261)
* update trusted hostname (1c30908)
* update trusted hostname (2cddc00)

## [0.43](https://gitlab.com/bubblehouse/django-moo/compare/v0.42.0...v0.43.0) (2026-01-19)

### Features

* instead of having the verb name as args[0], make it verb_name (5c61bc3)

## [0.42](https://gitlab.com/bubblehouse/django-moo/compare/v0.41.0...v0.42.0) (2026-01-19)

### Features

* begin to mimic LambdaCore in the `default` bootstrap configuration. (6f6434f)

## [0.41](https://gitlab.com/bubblehouse/django-moo/compare/v0.40.0...v0.41.0) (2025-09-06)

### Features

* add support for asterisk wildcard when creating verbs, closes [#8](https://gitlab.com/bubblehouse/django-moo/issues/8) (eb017ba)

## [0.40](https://gitlab.com/bubblehouse/django-moo/compare/v0.39.0...v0.40.0) (2025-08-30)

### Features

* added "either" dspec to support verbs with optional direct objects (31ae9a3)

## [0.39](https://gitlab.com/bubblehouse/django-moo/compare/v0.38.0...v0.39.0) (2025-06-22)

### Features

* support verb specifiers (f2ea0e3)

## [0.38](https://gitlab.com/bubblehouse/django-moo/compare/v0.37.1...v0.38.0) (2025-05-03)

### Features

* first release to PyPI (9357b30)

### Bug Fixes

* allow use of external packages, update docstrings (8ee3261)
* dependency fix for redis, move import (0fd6b65)
* improve method handling to handle system.describe() implementation (a65a03b)

## [0.37](https://gitlab.com/bubblehouse/django-moo/compare/v0.36.3...v0.37.1) (2025-03-16)

### Features

* added preliminary door support (e77ddef)
* implement getattr support for props and verbs (f2d1cf7)

### Bug Fixes

* door locking issues resolved (0711aba)
* handle verb names in methods properly (a5522e7)
* throw warnings when trying to write without redis (997e2df)
* getattr support for props and verbs (9586e6f)
* ignore methods when parsing for verbs (8644f0f)
* tests broken by parser changes (7c4969e)
* tests broken by parser changes (42939c3)

## [0.36](https://gitlab.com/bubblehouse/django-moo/compare/v0.35.0...v0.36.3) (2025-02-09)

### Features

* install a web-based ssh client on the root page (1216a1c)

### Bug Fixes

* dont remove shebang when bootstrapping (792d65a)
* final issues with verbs in debugger (f75ae53)
* prompt correctly updating from DB (fbe1d87)
* proper filename handling fixes debug issues (f4cdcfc)
* set __file__ when using a file-backed verb (9285e93)
* add viewport meta tag to fix mobile (b05506c)
* allow login form to wrap on smaller screens (13907f4)
* prevent wssh from being hijacked for other connections (417651f)
* hard-code hostname and port for webssh (00120ef)

## [0.35](https://gitlab.com/bubblehouse/django-moo/compare/v0.34.0...v0.35.0) (2025-01-24)

### Features

* add devcontainer support (d88812e)

## [0.34](https://gitlab.com/bubblehouse/django-moo/compare/v0.33.3...v0.34.0) (2025-01-12)

### Features

* reduce image size by using a builder image (ca20fc6)

## [0.33](https://gitlab.com/bubblehouse/django-moo/compare/v0.32.0...v0.33.3) (2025-01-12)

### Features

* implement serialization for moo types (2c2470f)

### Bug Fixes

* allow more look scenarios, update test (69f60f2)
* improve describe verb and add test (3a08e90)
* broken BBcode colors (d84f87f)
* improve create when using args (dd0b1bd)
* logging improvements (5909244)
* logging improvements for shell server (181c1fe)
* logging improvements for shell server (44efe39)
* quiet down celery (7005c7e)
* quiet down nginx, restore redirect (6759ea3)
* updated dependencies (47ff80d)
* class name consistency (4c46ab1)
* go verb needs to save the changes to caller location (cd752b0)
* use moo de-serialization for property values (07b76ce)

## [0.32](https://gitlab.com/bubblehouse/django-moo/compare/v0.31.0...v0.32.0) (2024-12-02)

### Features

* added has_property (e13f961)

### Bug Fixes

* restore default bootstrap after mistaking it for test (3312f1d)
* small tweaks and debug improvements for verbs (f0247c4)

## [0.31](https://gitlab.com/bubblehouse/django-moo/compare/v0.30.0...v0.31.0) (2024-11-30)

### Features

* first pass at room movement verbs (3d38859)
* improve verb loading (f14bbb5)
* move common boostrap code for universe into initialize_dataset (f3df4f5)

### Bug Fixes

* dont load from a file when the code is provided (6bb56d8)
* remove SFTP spike (6938154)
* verb cleanup (8e8f10c)

## [0.30](https://gitlab.com/bubblehouse/django-moo/compare/v0.29.2...v0.30.0) (2024-07-21)

### Features

* added sftp/scp support for editing verbs and properties (dcbe75f)

## [0.29](https://gitlab.com/bubblehouse/django-moo/compare/v0.28.0...v0.29.2) (2024-07-18)

### Features

* proper location change behavior, closes [#12](https://gitlab.com/bubblehouse/django-moo/issues/12) (32e94cb)

### Bug Fixes

* override delete() on Object, not AccessibleObject (a4c0860)
* check for recursion when changing location (f27c76a)

## [0.28](https://gitlab.com/bubblehouse/django-moo/compare/v0.27.0...v0.28.0) (2024-07-09)

### Features

* implement proper permissions and handlers for owners and locations (88e422a)

## [0.27](https://gitlab.com/bubblehouse/django-moo/compare/v0.26.0...v0.27.0) (2024-07-08)

### Features

* added object quotas and initialization (98b5d00)

## [0.26](https://gitlab.com/bubblehouse/django-moo/compare/v0.25.3...v0.26.0) (2024-07-05)

### Features

* began implementing support for background tasks (0e79a9a)

### Bug Fixes

* added db_index to important fields (1e72ccc)
* cleaned up invoke_verb, added docs (32b0724)
* rename functions (3001aa0)

## [0.25](https://gitlab.com/bubblehouse/django-moo/compare/v0.24.0...v0.25.3) (2024-07-04)

### Features

* improved prompt, some refactoring (3ec3b2d)

### Bug Fixes

* correctly handle ctrl-D (b0558c7)
* sleep before starting server to give time for the previous server port to be closed (86b247b)
* added missing lookup() function (fb41cc6)
* fixed use of args/kwargs with multiple verb invocations (f7711e1)
* consolidate custom verb functions in moo.core (e3c9329)

## [0.24](https://gitlab.com/bubblehouse/django-moo/compare/v0.23.0...v0.24.0) (2024-06-10)

### Features

* simplified client code and removed Python REPL (b035087)

## [0.23](https://gitlab.com/bubblehouse/django-moo/compare/v0.22.0...v0.23.0) (2024-06-09)

### Features

* allow sending messages directly to a user (444ce9a)

## [0.22](https://gitlab.com/bubblehouse/django-moo/compare/v0.21.0...v0.22.0) (2024-05-20)

### Features

* add a celery runner to docker-compose (a218f3e)
* add celery with django and redis integration (6eadf15)
* configure django/celery intergration (88654f7)
* run verb code in Celery workers instead of the web application (bab48ee)

### Bug Fixes

* only run watchedo on moo_shell invocations (ffcf3f4)

## [0.21](https://gitlab.com/bubblehouse/django-moo/compare/v0.20.0...v0.21.0) (2024-05-07)

### Features

* added moo_enableuser command (1be7daf)

## [0.20](https://gitlab.com/bubblehouse/django-moo/compare/v0.19.0...v0.20.0) (2024-05-07)

### Features

* use ACE editor inside the Django admin for editing Verbs (2c0a1d6)

### Bug Fixes

* handle direct object ID lookups (aec1cf5)

## [0.19](https://gitlab.com/bubblehouse/django-moo/compare/v0.18.2...v0.19.0) (2024-05-06)

### Features

* add intrinsic `obvious` property to improve object searching (97a7d62)
* added contents to look output (92b41ea)

### Bug Fixes

* added more safe builtins (476cf3c)
* improved `look` command with better functionality and ANSI colors (e872eec)

## [0.18](https://gitlab.com/bubblehouse/django-moo/compare/v0.17.4...v0.18.2) (2024-05-02)

### Features

* enable Rich-based markup processing on output (b3a3e27)

### Bug Fixes

* improve var handling (acd163c)
* dont stringify things being printed (5694467)

## [0.17](https://gitlab.com/bubblehouse/django-moo/compare/v0.16.0...v0.17.4) (2024-04-28)

### Features

* formally released as django-moo (e519798)

### Bug Fixes

* prompt improvements (1e49817)
* use existing hosts (1c8b09c)
* set permissions so www-data can use the host key (50aeb5a)
* add some missing fields, include extras in the package so it can build a Docker container (cc86019)
* packaging naming (19c5562)
* quiet build warnings about this plugin (34f7a18)
* updated lockfile (135be75)

## [0.16](https://gitlab.com/bubblehouse/django-moo/compare/v0.15.1...v0.16.0) (2024-03-23)

### Features

* begin integrating ACLs (7edb982)

## [0.15](https://gitlab.com/bubblehouse/django-moo/compare/v0.14.8...v0.15.1) (2024-03-17)

### Features

* add inherited field to property (081cf38)
* add object.invoke_verb() (7da3d28)
* added add_ancestor with inheritence of properties (9c6113b)
* added alternate prompt mode for MUD mode (c530a1f)
* added parser/lexer, very early successes with each (747f598)
* get_property will now recurse the inheritance tree (12090ee)
* ssh prompt now defaults to sentence parser (15d1251)

### Bug Fixes

* changed location of chart (083e2f7)
* aliases work inside the parser now (45fb2d5)
* always use Accessible- objects if they will be used in a restricted env (1c3c8dc)
* be clear about which dataset is being used (7c70b2d)
* correctly clone instances (90194d6)
* dont massage verb code in prompt (d6b6429)
* fixes for permissions and associated tests (eed7c9a)
* make get ancestors/descendents generators so we can stop once we find something (3845247)
* prepositions and handle query sets (a25499e)
* remove invalid/unneeded related names (2af5ba1)
* remove invalid/unneeded related names (4e87d55)
* remove magic variables (3e2d9e0)
* typo in exception message (c8ac77b)
* update to python3.11 (0f21ed4)
* use a single eval function for both (06f8b5a)
* use signals instead of overriding through.save() (7343898)
* use warnings instead of logging them (4a2a673)
* verb environment globals (41e5365)

## [0.14](https://gitlab.com/bubblehouse/django-moo/compare/v0.13.2...v0.14.8) (2023-12-18)

### Features

* use a context manager around code invocations (f82a23c)

### Bug Fixes

* provide an output for the context (02a09d6)
* more verb reload updates (ea9e984)
* output now sent to client instead of log (7858155)
* further improvements to syntax sugar (bcf34a5)
* sketching out first verb (9c779ec)
* starting to implement proper context support (ffc2159)
* updated to Django 5.0 (47e30c6)
* add owner variable to add_* methods (b4796da)
* remove observations, that concept doesnt exist here (58935da)
* add_propery and add_verb updates (3fbfe4c)
* use correct PK for system (afbd6ea)
* bootstrap naming tweaks, trying to add first properties with little success (4295497)
* correct verb handling scenarios (6e5a5d8)
* include repo for reloadable verbs (c057478)
* other login fixes, still having exec trouble (e1d7a3e)

## [0.13](https://gitlab.com/bubblehouse/django-moo/compare/v0.12.0...v0.13.2) (2023-12-10)

### Features

* integrate Python shell with restricted environment (f1155e3)

### Bug Fixes

* remove os.system() loophole and prep for further customization (84f3985)
* hold on to get/set_caller until we have a replacement for verb to use (18c07ad)
* its okay to save the whole model object (bade6a0)
* active user not so simple (96d17cb)
* instead of trying to use contextvars within a thread, just pass the user_id along (24a2a3f)

## [0.12](https://gitlab.com/bubblehouse/django-moo/compare/v0.11.0...v0.12.0) (2023-12-04)

### Features

* add support for SSH key login (cbb00b4)

## [0.11](https://gitlab.com/bubblehouse/django-moo/compare/v0.10.4...v0.11.0) (2023-12-04)

### Features

* use Django user to authenticate (8e11f94)

## [0.10](https://gitlab.com/bubblehouse/django-moo/compare/v0.9.0...v0.10.4) (2023-12-03)

### Features

* ownership and ACL support (a1c96ca)

### Bug Fixes

* raw id field (a79710d)
* raw id field (5573c4e)
* add Player model for User/Avatar integration (02b8f68)
* add Player model for User/Avatar integration (4554112)
* bootstrapping issues, refactoring (f24f4d3)

## [0.9](https://gitlab.com/bubblehouse/django-moo/compare/v0.8.0...v0.9.0) (2023-12-03)

### Features

* replace temp shell with python repl (ed75b0a)

## [0.8](https://gitlab.com/bubblehouse/django-moo/compare/v0.7.0...v0.8.0) (2023-11-30)

### Features

* created db init script (6436a54)

### Bug Fixes

* continuing to address init issues (05b7fa9)
* implementing more permissions details, refactoring (f7534fc)

## [0.7](https://gitlab.com/bubblehouse/django-moo/compare/v0.6.0...v0.7.0) (2023-11-27)

### Features

* begin implementing code execution (ec1ad55)

## [0.6](https://gitlab.com/bubblehouse/django-moo/compare/v0.5.0...v0.6.0) (2023-11-14)

### Features

* created core app with model imported from antioch (1cd61be)

## [0.5](https://gitlab.com/bubblehouse/django-moo/compare/v0.4.3...v0.5.0) (2023-11-04)

### Features

* fully interactive SSH prompt using `python-prompt-toolkit` (d9e567d)
* setup postgres settings for dev and local (7361ccf)

### Bug Fixes

* force release (014d462)
* force release (1e8641c)
* force release (f3b4a8f)
* force release (6d296a1)

## [0.4](https://gitlab.com/bubblehouse/django-moo/compare/v0.3.7...v0.4.3) (2023-10-10)

### Features

* add shell to compose file (7704588)

### Bug Fixes

* configure logging (942743b)
* dont try to install native python modules (48a7a9c)
* use correct listening address (1cbed76)
* helm chart selector labels for shell service (02beba3)
* use port name (26b7379)
* port for shell service (4d0df41)

## [0.3](https://gitlab.com/bubblehouse/django-moo/compare/v0.2.3...v0.3.7) (2023-09-23)

### Features

* implement a trivial SSH server as a Django Management command (9291f50)

### Bug Fixes

* installed uwsgi-python3 and net-tools (7ded073)
* remove broken redirect (fd38705)
* disable liveness/readiness for ssh server for now (221434b)
* change ownership of server key (cf23255)
* force release (c977ec7)
* generate a key inside the Dockfile (9bcf9e8)
* generate a key inside the Dockfile (a46d0cc)
* install ssh (e6e3f3f)
* mixed up service ports (0376e5b)
* chart typo (00bcb1a)
* port updates (4041617)

## [0.2](https://gitlab.com/bubblehouse/django-moo/compare/v0.1.4...v0.2.3) (2023-09-17)

### Features

* added Rich library (72787b5)

### Bug Fixes

* disabled DBs and cache temporarily in dev, moved around environment names (29462b6)
* ingress port correction (6af8a74)
* chart typo (53872e6)
* force release (f750eb3)
* more setup and Django settings refactoring (47a0bac)

## [0.1](https://gitlab.com/bubblehouse/django-moo/compare/v0.1.0...v0.1.4) (2023-09-17)

### Bug Fixes

* avoid pinning Python version, include wheel as release attachment (f83b300)
* force release (153af17)
* start using base image (21295d3)
* use poetry publish (d966ff4)
* chart semantic-release version (42aeae4)
* update chart image (9bf0976)
* chart semantic-release version missing files (bbccce5)
* chart semantic-release version missing files (579ca1a)
