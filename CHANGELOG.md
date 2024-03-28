## [0.16.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.15.1...v0.16.0) (2024-03-23)


### Features

* begin integrating ACLs ([7edb982](https://gitlab.com/bubblehouse/django-moo/commit/7edb982b1bb0193398301d8fd09f85d8e2f3a64c))

## [0.15.1](https://gitlab.com/bubblehouse/django-moo/compare/v0.15.0...v0.15.1) (2024-03-17)


### Bug Fixes

* changed location of chart ([083e2f7](https://gitlab.com/bubblehouse/django-moo/commit/083e2f74206bcd844a677c3cd2496f6ca0689c58))

## [0.15.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.14.8...v0.15.0) (2024-03-17)


### Features

* add inherited field to property ([081cf38](https://gitlab.com/bubblehouse/django-moo/commit/081cf383ae88cc3c62c091d17210d4357c6df634))
* add object.invoke_verb() ([7da3d28](https://gitlab.com/bubblehouse/django-moo/commit/7da3d283ddae62b488269fa26f8167f1182f382a))
* added add_ancestor with inheritence of properties ([9c6113b](https://gitlab.com/bubblehouse/django-moo/commit/9c6113b55dab28b4f4fe8cc5cdf6b0c95a0f5507))
* added alternate prompt mode for MUD mode ([c530a1f](https://gitlab.com/bubblehouse/django-moo/commit/c530a1fc4cdf5ac3505c6c6de53dd4d9d62f0051))
* added parser/lexer, very early successes with each ([747f598](https://gitlab.com/bubblehouse/django-moo/commit/747f5988b100a6e9ae1fa1c3e8b0892dc7b777f8))
* get_property will now recurse the inheritance tree ([12090ee](https://gitlab.com/bubblehouse/django-moo/commit/12090ee61847bc346ba8235a7b648947b78a223a))
* ssh prompt now defaults to sentence parser ([15d1251](https://gitlab.com/bubblehouse/django-moo/commit/15d1251b8d3558b3dcf643f2bf65ffa89001e70f))


### Bug Fixes

* aliases work inside the parser now ([45fb2d5](https://gitlab.com/bubblehouse/django-moo/commit/45fb2d5d5ffb56b3b1ef44d33e0a2c670c2906bd))
* always use Accessible- objects if they will be used in a restricted env ([1c3c8dc](https://gitlab.com/bubblehouse/django-moo/commit/1c3c8dcad10e20f9344f2c544ba3c74aa67519e1))
* be clear about which dataset is being used ([7c70b2d](https://gitlab.com/bubblehouse/django-moo/commit/7c70b2dd01338e8e50f11208e0ed048edaf28f2a))
* correctly clone instances ([90194d6](https://gitlab.com/bubblehouse/django-moo/commit/90194d63092f447b43c7335bb76dd5f9642e801c))
* dont massage verb code in prompt ([d6b6429](https://gitlab.com/bubblehouse/django-moo/commit/d6b6429b4b355fd4372458a5da733c8e9f3ed787))
* fixes for permissions and associated tests ([eed7c9a](https://gitlab.com/bubblehouse/django-moo/commit/eed7c9a563218c999662f22acb779ce752846622))
* make get ancestors/descendents generators so we can stop once we find something ([3845247](https://gitlab.com/bubblehouse/django-moo/commit/3845247d3ed6a27465611983180bcb8cad064471))
* prepositions and handle query sets ([a25499e](https://gitlab.com/bubblehouse/django-moo/commit/a25499eb2a5cc17419290ae7c91aeaa16fa23499))
* remove invalid/unneeded related names ([2af5ba1](https://gitlab.com/bubblehouse/django-moo/commit/2af5ba12929153e7d0622f375703045ddd5cb8c1))
* remove invalid/unneeded related names ([4e87d55](https://gitlab.com/bubblehouse/django-moo/commit/4e87d550966b57b2d555b0940a03a6a7bddd5853))
* remove magic variables ([3e2d9e0](https://gitlab.com/bubblehouse/django-moo/commit/3e2d9e0ae354b1f2b0a5973276ad7086a408a68e))
* typo in exception message ([c8ac77b](https://gitlab.com/bubblehouse/django-moo/commit/c8ac77b6b0375e2213ce347b8594c5469c128641))
* update to python3.11 ([0f21ed4](https://gitlab.com/bubblehouse/django-moo/commit/0f21ed42d9bd95d3228d22b67096e0730de91630))
* use a single eval function for both ([06f8b5a](https://gitlab.com/bubblehouse/django-moo/commit/06f8b5a0be2a28882d37abf78c1b78093b02d2fe))
* use signals instead of overriding through.save() ([7343898](https://gitlab.com/bubblehouse/django-moo/commit/7343898ddd0a97c9bab60884cc0071bef5b26309))
* use warnings instead of logging them ([4a2a673](https://gitlab.com/bubblehouse/django-moo/commit/4a2a6737ca95e025b006a3d4bf3046ea58a304bb))
* verb environment globals ([41e5365](https://gitlab.com/bubblehouse/django-moo/commit/41e5365e3020dcdb399f0101650023d5d3b4993a))

## [0.14.8](https://gitlab.com/bubblehouse/django-moo/compare/v0.14.7...v0.14.8) (2023-12-18)


### Bug Fixes

* provide an output for the context ([02a09d6](https://gitlab.com/bubblehouse/django-moo/commit/02a09d655407d0ba1993daec3072a3754291912b))

## [0.14.7](https://gitlab.com/bubblehouse/django-moo/compare/v0.14.6...v0.14.7) (2023-12-18)


### Bug Fixes

* more verb reload updates ([ea9e984](https://gitlab.com/bubblehouse/django-moo/commit/ea9e984edd79df4f5f09f7bee7026a26236ac3e8))
* output now sent to client instead of log ([7858155](https://gitlab.com/bubblehouse/django-moo/commit/7858155c4d6dd08d9cb43c806725c59b366e4db6))

## [0.14.6](https://gitlab.com/bubblehouse/django-moo/compare/v0.14.5...v0.14.6) (2023-12-17)


### Bug Fixes

* further improvements to syntax sugar ([bcf34a5](https://gitlab.com/bubblehouse/django-moo/commit/bcf34a5d6dc3fc7f61b54795decda013c87f5baf))

## [0.14.5](https://gitlab.com/bubblehouse/django-moo/compare/v0.14.4...v0.14.5) (2023-12-17)


### Bug Fixes

* sketching out first verb ([9c779ec](https://gitlab.com/bubblehouse/django-moo/commit/9c779ec0e08f7c7cac4a96f8265c0b3da9832e2f))
* starting to implement proper context support ([ffc2159](https://gitlab.com/bubblehouse/django-moo/commit/ffc2159f848b009317c2e695c822aabaf59312f1))
* updated to Django 5.0 ([47e30c6](https://gitlab.com/bubblehouse/django-moo/commit/47e30c6ba0cce2db4b16365124df7aede8447de3))

## [0.14.4](https://gitlab.com/bubblehouse/django-moo/compare/v0.14.3...v0.14.4) (2023-12-17)


### Bug Fixes

* add owner variable to add_* methods ([b4796da](https://gitlab.com/bubblehouse/django-moo/commit/b4796dade2b65c7085b6fd8a2120a276659bd5ac))
* remove observations, that concept doesnt exist here ([58935da](https://gitlab.com/bubblehouse/django-moo/commit/58935daf262fe4c192f27ce7f1a65b6c1bc3ae06))

## [0.14.3](https://gitlab.com/bubblehouse/django-moo/compare/v0.14.2...v0.14.3) (2023-12-17)


### Bug Fixes

* add_propery and add_verb updates ([3fbfe4c](https://gitlab.com/bubblehouse/django-moo/commit/3fbfe4ca38c1ec160b6dc3cc8b033336eac47301))
* use correct PK for system ([afbd6ea](https://gitlab.com/bubblehouse/django-moo/commit/afbd6ea965ddf7b0f4280889915d4aaad1a42c0d))

## [0.14.2](https://gitlab.com/bubblehouse/django-moo/compare/v0.14.1...v0.14.2) (2023-12-16)


### Bug Fixes

* bootstrap naming tweaks, trying to add first properties with little success ([4295497](https://gitlab.com/bubblehouse/django-moo/commit/4295497b3ee25bae264d75580cc6258ccd2d352a))
* correct verb handling scenarios ([6e5a5d8](https://gitlab.com/bubblehouse/django-moo/commit/6e5a5d83301643f465961911c573533161444be9))
* include repo for reloadable verbs ([c057478](https://gitlab.com/bubblehouse/django-moo/commit/c057478327c040c2547ea7446f0b28db5c72ab66))

## [0.14.1](https://gitlab.com/bubblehouse/django-moo/compare/v0.14.0...v0.14.1) (2023-12-11)


### Bug Fixes

* other login fixes, still having exec trouble ([e1d7a3e](https://gitlab.com/bubblehouse/django-moo/commit/e1d7a3ecf5f4736c10081d798eb5ef050cb94af4))

## [0.14.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.13.2...v0.14.0) (2023-12-11)


### Features

* use a context manager around code invocations ([f82a23c](https://gitlab.com/bubblehouse/django-moo/commit/f82a23c88d2a9c76db53cf5742120dfce3193ff4))

## [0.13.2](https://gitlab.com/bubblehouse/django-moo/compare/v0.13.1...v0.13.2) (2023-12-10)


### Bug Fixes

* hold on to get/set_caller until we have a replacement for verb to use ([18c07ad](https://gitlab.com/bubblehouse/django-moo/commit/18c07ad62701b643b79aa16748ec55f07e4f4ef1))
* its okay to save the whole model object ([bade6a0](https://gitlab.com/bubblehouse/django-moo/commit/bade6a0c199bf5ca65eb8350894c33cc9835c6b1))

## [0.13.1](https://gitlab.com/bubblehouse/django-moo/compare/v0.13.0...v0.13.1) (2023-12-10)


### Bug Fixes

* active user not so simple ([96d17cb](https://gitlab.com/bubblehouse/django-moo/commit/96d17cb1b4f518503b86040342cf824893ead91a))
* instead of trying to use contextvars within a thread, just pass the user_id along ([24a2a3f](https://gitlab.com/bubblehouse/django-moo/commit/24a2a3fea13b8818995727d5306d6695ec4755ab))

## [0.13.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.12.0...v0.13.0) (2023-12-08)


### Features

* integrate Python shell with restricted environment ([f1155e3](https://gitlab.com/bubblehouse/django-moo/commit/f1155e3314050c7112cb7f13b363480dcfd444b4))


### Bug Fixes

* remove os.system() loophole and prep for further customization ([84f3985](https://gitlab.com/bubblehouse/django-moo/commit/84f3985cf2b635a96e9c1e34f755bdf7e9ae4351))

## [0.12.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.11.0...v0.12.0) (2023-12-04)


### Features

* add support for SSH key login ([cbb00b4](https://gitlab.com/bubblehouse/django-moo/commit/cbb00b49a92459ee8d881edde061d46ea04efb95))

## [0.11.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.10.4...v0.11.0) (2023-12-04)


### Features

* use Django user to authenticate ([8e11f94](https://gitlab.com/bubblehouse/django-moo/commit/8e11f9407bb87c918e6c92dcf8ebbaa2b32d42c7))

## [0.10.4](https://gitlab.com/bubblehouse/django-moo/compare/v0.10.3...v0.10.4) (2023-12-03)


### Bug Fixes

* raw id field ([a79710d](https://gitlab.com/bubblehouse/django-moo/commit/a79710de92b247f63705d7aed330daa326048363))

## [0.10.3](https://gitlab.com/bubblehouse/django-moo/compare/v0.10.2...v0.10.3) (2023-12-03)


### Bug Fixes

* raw id field ([5573c4e](https://gitlab.com/bubblehouse/django-moo/commit/5573c4efffaab10c77f4adf4ef03ad8cc3b2ec11))

## [0.10.2](https://gitlab.com/bubblehouse/django-moo/compare/v0.10.1...v0.10.2) (2023-12-03)


### Bug Fixes

* add Player model for User/Avatar integration ([02b8f68](https://gitlab.com/bubblehouse/django-moo/commit/02b8f6867266d184749aaa2df09f9d1af2ebb10b))
* add Player model for User/Avatar integration ([4554112](https://gitlab.com/bubblehouse/django-moo/commit/45541125224c2fe43915f07feea48f3f011ea626))

## [0.10.1](https://gitlab.com/bubblehouse/django-moo/compare/v0.10.0...v0.10.1) (2023-12-03)


### Bug Fixes

* bootstrapping issues, refactoring ([f24f4d3](https://gitlab.com/bubblehouse/django-moo/commit/f24f4d3aa6be6427d1a29a90cbbb97e455e6f932))

## [0.10.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.9.0...v0.10.0) (2023-12-03)


### Features

* ownership and ACL support ([a1c96ca](https://gitlab.com/bubblehouse/django-moo/commit/a1c96ca82e55eb0a40a03c4a4909ef67593ad022))

## [0.9.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.8.0...v0.9.0) (2023-12-03)


### Features

* replace temp shell with python repl ([ed75b0a](https://gitlab.com/bubblehouse/django-moo/commit/ed75b0ac1c5eb49f901c3af55e1fd0499e4983c8))

## [0.8.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.7.0...v0.8.0) (2023-11-30)


### Features

* created db init script ([6436a54](https://gitlab.com/bubblehouse/django-moo/commit/6436a54df2628baed601cf8b875a1f1884992613))


### Bug Fixes

* continuing to address init issues ([05b7fa9](https://gitlab.com/bubblehouse/django-moo/commit/05b7fa9786215e8d16bef6d54e490b02496620e9))
* implementing more permissions details, refactoring ([f7534fc](https://gitlab.com/bubblehouse/django-moo/commit/f7534fca30242f4ab346b16747f1eeb880926acb))

## [0.7.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.6.0...v0.7.0) (2023-11-27)


### Features

* begin implementing code execution ([ec1ad55](https://gitlab.com/bubblehouse/django-moo/commit/ec1ad55d3778a8ac4121db714401b0d158cb20fe))

## [0.6.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.5.0...v0.6.0) (2023-11-14)


### Features

* created core app with model imported from antioch ([1cd61be](https://gitlab.com/bubblehouse/django-moo/commit/1cd61be9ef33e52c77d1088ff75403aa3d9c3d87))

## [0.5.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.4.3...v0.5.0) (2023-11-04)


### Features

* fully interactive SSH prompt using `python-prompt-toolkit` ([d9e567d](https://gitlab.com/bubblehouse/django-moo/commit/d9e567d3674c93ad210c2fc6c1f412f4c07f6a7f))
* setup postgres settings for dev and local ([7361ccf](https://gitlab.com/bubblehouse/django-moo/commit/7361ccfff781b98f9c4c51e364217bd91e2e164f))


### Bug Fixes

* force release ([014d462](https://gitlab.com/bubblehouse/django-moo/commit/014d4620de1cf6eea0aebcfde2e65642a5401464))
* force release ([1e8641c](https://gitlab.com/bubblehouse/django-moo/commit/1e8641c39e250b3f9d7f6d35d1b0fcf5211559af))
* force release ([f3b4a8f](https://gitlab.com/bubblehouse/django-moo/commit/f3b4a8fb7b061802115480c48ed9b7491d50449f))
* force release ([6d296a1](https://gitlab.com/bubblehouse/django-moo/commit/6d296a1ed3a53ef78776ec4bb169188aa648e285))

## [0.4.3](https://gitlab.com/bubblehouse/django-moo/compare/v0.4.2...v0.4.3) (2023-10-10)


### Bug Fixes

* helm chart selector labels for shell service ([02beba3](https://gitlab.com/bubblehouse/django-moo/commit/02beba38f8e71f797884d56eb09c8bf448622656))

## [0.4.2](https://gitlab.com/bubblehouse/django-moo/compare/v0.4.1...v0.4.2) (2023-10-10)


### Bug Fixes

* use port name ([26b7379](https://gitlab.com/bubblehouse/django-moo/commit/26b73791b1a9c2fe4aabf240423eb5688c113a0e))

## [0.4.1](https://gitlab.com/bubblehouse/django-moo/compare/v0.4.0...v0.4.1) (2023-10-10)


### Bug Fixes

* port for shell service ([4d0df41](https://gitlab.com/bubblehouse/django-moo/commit/4d0df4146e895a9ebf5c343861766c01dd8a1a34))

## [0.4.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.3.7...v0.4.0) (2023-09-30)


### Features

* add shell to compose file ([7704588](https://gitlab.com/bubblehouse/django-moo/commit/77045880128cc934bd912e6d5b8c7e0e1d6fc62d))


### Bug Fixes

* configure logging ([942743b](https://gitlab.com/bubblehouse/django-moo/commit/942743b6da1346e0de481624b8c9e69f58584245))
* dont try to install native python modules ([48a7a9c](https://gitlab.com/bubblehouse/django-moo/commit/48a7a9c4b9301d28bad97b6778ccc0d4823aaabb))
* use correct listening address ([1cbed76](https://gitlab.com/bubblehouse/django-moo/commit/1cbed76ac2e888ac29f674052facf1a686589642))

## [0.3.7](https://gitlab.com/bubblehouse/django-moo/compare/v0.3.6...v0.3.7) (2023-09-23)


### Bug Fixes

* installed uwsgi-python3 and net-tools ([7ded073](https://gitlab.com/bubblehouse/django-moo/commit/7ded073f9acb9e965bb98c7eeb9e6edf2c94d2ef))

## [0.3.6](https://gitlab.com/bubblehouse/django-moo/compare/v0.3.5...v0.3.6) (2023-09-19)


### Bug Fixes

* remove broken redirect ([fd38705](https://gitlab.com/bubblehouse/django-moo/commit/fd3870595ee758c17955ac9622c5794ec651a074))

## [0.3.5](https://gitlab.com/bubblehouse/django-moo/compare/v0.3.4...v0.3.5) (2023-09-19)


### Bug Fixes

* disable liveness/readiness for ssh server for now ([221434b](https://gitlab.com/bubblehouse/django-moo/commit/221434bb18b30432707feabbdee4b8ede2de6fb6))

## [0.3.4](https://gitlab.com/bubblehouse/django-moo/compare/v0.3.3...v0.3.4) (2023-09-19)


### Bug Fixes

* change ownership of server key ([cf23255](https://gitlab.com/bubblehouse/django-moo/commit/cf232550c426c054327a8cc4c55bb0f8a36b3c08))

## [0.3.3](https://gitlab.com/bubblehouse/django-moo/compare/v0.3.2...v0.3.3) (2023-09-19)


### Bug Fixes

* force release ([c977ec7](https://gitlab.com/bubblehouse/django-moo/commit/c977ec75a8f3aaaa927918844d97f02aebaac0cd))
* generate a key inside the Dockfile ([9bcf9e8](https://gitlab.com/bubblehouse/django-moo/commit/9bcf9e8646224cce521a0a5ff82974931a4b8e8a))
* generate a key inside the Dockfile ([a46d0cc](https://gitlab.com/bubblehouse/django-moo/commit/a46d0cc8fedb6b631eee8f58f5ea9edd2f686c29))
* install ssh ([e6e3f3f](https://gitlab.com/bubblehouse/django-moo/commit/e6e3f3f2951c630672c05bc2705ef684694d7021))
* mixed up service ports ([0376e5b](https://gitlab.com/bubblehouse/django-moo/commit/0376e5b424edb20e7b35a7085b0c6c58a3f48f77))

## [0.3.2](https://gitlab.com/bubblehouse/django-moo/compare/v0.3.1...v0.3.2) (2023-09-19)


### Bug Fixes

* chart typo ([00bcb1a](https://gitlab.com/bubblehouse/django-moo/commit/00bcb1a218c6353f31a36850fb41c9f29a5cf015))

## [0.3.1](https://gitlab.com/bubblehouse/django-moo/compare/v0.3.0...v0.3.1) (2023-09-19)


### Bug Fixes

* port updates ([4041617](https://gitlab.com/bubblehouse/django-moo/commit/4041617ea99f9e287ab95d429b9d337cdc3e9164))

## [0.3.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.2.3...v0.3.0) (2023-09-18)


### Features

* implement a trivial SSH server as a Django Management command ([9291f50](https://gitlab.com/bubblehouse/django-moo/commit/9291f50ff55ad31c227b974ef42d94152bf278da))

## [0.2.3](https://gitlab.com/bubblehouse/django-moo/compare/v0.2.2...v0.2.3) (2023-09-17)


### Bug Fixes

* ingress port correction ([6af8a74](https://gitlab.com/bubblehouse/django-moo/commit/6af8a743b05b6febdce8ed5501c976839e93ccdc))

## [0.2.2](https://gitlab.com/bubblehouse/django-moo/compare/v0.2.1...v0.2.2) (2023-09-17)


### Bug Fixes

* chart typo ([53872e6](https://gitlab.com/bubblehouse/django-moo/commit/53872e673d68dcff7b57fd5fd2189529805ad559))
* force release ([f750eb3](https://gitlab.com/bubblehouse/django-moo/commit/f750eb3aaef3e1311af394676df3a908bc155c8b))

## [0.2.1](https://gitlab.com/bubblehouse/django-moo/compare/v0.2.0...v0.2.1) (2023-09-17)


### Bug Fixes

* more setup and Django settings refactoring ([47a0bac](https://gitlab.com/bubblehouse/django-moo/commit/47a0bacb129ca7047de78b9e748fd09de9ef0420))

## [0.2.0](https://gitlab.com/bubblehouse/django-moo/compare/v0.1.4...v0.2.0) (2023-09-17)


### Features

* added Rich library ([72787b5](https://gitlab.com/bubblehouse/django-moo/commit/72787b569d4d40b6655537af459e7dfb9d41f115))


### Bug Fixes

* disabled DBs and cache temporarily in dev, moved around environment names ([29462b6](https://gitlab.com/bubblehouse/django-moo/commit/29462b6778b1e17be8e8355ed50837c5d5d0ca93))

## [0.1.4](https://gitlab.com/bubblehouse/django-moo/compare/v0.1.3...v0.1.4) (2023-09-17)


### Bug Fixes

* chart semantic-release version missing files ([bbccce5](https://gitlab.com/bubblehouse/django-moo/commit/bbccce510cbb11a825b95253ee3ee62220732bb9))
* chart semantic-release version missing files ([579ca1a](https://gitlab.com/bubblehouse/django-moo/commit/579ca1a305716b0a97b88b6712e03514cf8e1b1c))

## [0.1.3](https://gitlab.com/bubblehouse/django-moo/compare/v0.1.2...v0.1.3) (2023-09-17)


### Bug Fixes

* chart semantic-release version ([42aeae4](https://gitlab.com/bubblehouse/django-moo/commit/42aeae49fa500b11333ecc2b9568429980916ebe))

## [0.1.2](https://gitlab.com/bubblehouse/django-moo/compare/v0.1.1...v0.1.2) (2023-09-17)


### Bug Fixes

* update chart image ([9bf0976](https://gitlab.com/bubblehouse/django-moo/commit/9bf0976ae25f28e194ccc5bb713733e5b1772551))

## [0.1.1](https://gitlab.com/bubblehouse/django-moo/compare/v0.1.0...v0.1.1) (2023-09-17)


### Bug Fixes

* avoid pinning Python version, include wheel as release attachment ([f83b300](https://gitlab.com/bubblehouse/django-moo/commit/f83b300be9968fb20c57412868d2c64c87c53b9f))
* force release ([153af17](https://gitlab.com/bubblehouse/django-moo/commit/153af17ebf97acd38fbac0c33ffe3c7afc8cf38d))
* start using base image ([21295d3](https://gitlab.com/bubblehouse/django-moo/commit/21295d3751382b4711e2c2a07d8b3c0fbc248ee9))
* use poetry publish ([d966ff4](https://gitlab.com/bubblehouse/django-moo/commit/d966ff4a2f3ccfc5b48f22009f520df7aa1cede8))
