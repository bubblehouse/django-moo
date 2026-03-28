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
