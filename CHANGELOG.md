## [0.14.4](https://gitlab.com/bubblehouse/termiverse/compare/v0.14.3...v0.14.4) (2023-12-17)


### Bug Fixes

* add owner variable to add_* methods ([b4796da](https://gitlab.com/bubblehouse/termiverse/commit/b4796dade2b65c7085b6fd8a2120a276659bd5ac))
* remove observations, that concept doesnt exist here ([58935da](https://gitlab.com/bubblehouse/termiverse/commit/58935daf262fe4c192f27ce7f1a65b6c1bc3ae06))

## [0.14.3](https://gitlab.com/bubblehouse/termiverse/compare/v0.14.2...v0.14.3) (2023-12-17)


### Bug Fixes

* add_propery and add_verb updates ([3fbfe4c](https://gitlab.com/bubblehouse/termiverse/commit/3fbfe4ca38c1ec160b6dc3cc8b033336eac47301))
* use correct PK for system ([afbd6ea](https://gitlab.com/bubblehouse/termiverse/commit/afbd6ea965ddf7b0f4280889915d4aaad1a42c0d))

## [0.14.2](https://gitlab.com/bubblehouse/termiverse/compare/v0.14.1...v0.14.2) (2023-12-16)


### Bug Fixes

* bootstrap naming tweaks, trying to add first properties with little success ([4295497](https://gitlab.com/bubblehouse/termiverse/commit/4295497b3ee25bae264d75580cc6258ccd2d352a))
* correct verb handling scenarios ([6e5a5d8](https://gitlab.com/bubblehouse/termiverse/commit/6e5a5d83301643f465961911c573533161444be9))
* include repo for reloadable verbs ([c057478](https://gitlab.com/bubblehouse/termiverse/commit/c057478327c040c2547ea7446f0b28db5c72ab66))

## [0.14.1](https://gitlab.com/bubblehouse/termiverse/compare/v0.14.0...v0.14.1) (2023-12-11)


### Bug Fixes

* other login fixes, still having exec trouble ([e1d7a3e](https://gitlab.com/bubblehouse/termiverse/commit/e1d7a3ecf5f4736c10081d798eb5ef050cb94af4))

## [0.14.0](https://gitlab.com/bubblehouse/termiverse/compare/v0.13.2...v0.14.0) (2023-12-11)


### Features

* use a context manager around code invocations ([f82a23c](https://gitlab.com/bubblehouse/termiverse/commit/f82a23c88d2a9c76db53cf5742120dfce3193ff4))

## [0.13.2](https://gitlab.com/bubblehouse/termiverse/compare/v0.13.1...v0.13.2) (2023-12-10)


### Bug Fixes

* hold on to get/set_caller until we have a replacement for verb to use ([18c07ad](https://gitlab.com/bubblehouse/termiverse/commit/18c07ad62701b643b79aa16748ec55f07e4f4ef1))
* its okay to save the whole model object ([bade6a0](https://gitlab.com/bubblehouse/termiverse/commit/bade6a0c199bf5ca65eb8350894c33cc9835c6b1))

## [0.13.1](https://gitlab.com/bubblehouse/termiverse/compare/v0.13.0...v0.13.1) (2023-12-10)


### Bug Fixes

* active user not so simple ([96d17cb](https://gitlab.com/bubblehouse/termiverse/commit/96d17cb1b4f518503b86040342cf824893ead91a))
* instead of trying to use contextvars within a thread, just pass the user_id along ([24a2a3f](https://gitlab.com/bubblehouse/termiverse/commit/24a2a3fea13b8818995727d5306d6695ec4755ab))

## [0.13.0](https://gitlab.com/bubblehouse/termiverse/compare/v0.12.0...v0.13.0) (2023-12-08)


### Features

* integrate Python shell with restricted environment ([f1155e3](https://gitlab.com/bubblehouse/termiverse/commit/f1155e3314050c7112cb7f13b363480dcfd444b4))


### Bug Fixes

* remove os.system() loophole and prep for further customization ([84f3985](https://gitlab.com/bubblehouse/termiverse/commit/84f3985cf2b635a96e9c1e34f755bdf7e9ae4351))

## [0.12.0](https://gitlab.com/bubblehouse/termiverse/compare/v0.11.0...v0.12.0) (2023-12-04)


### Features

* add support for SSH key login ([cbb00b4](https://gitlab.com/bubblehouse/termiverse/commit/cbb00b49a92459ee8d881edde061d46ea04efb95))

## [0.11.0](https://gitlab.com/bubblehouse/termiverse/compare/v0.10.4...v0.11.0) (2023-12-04)


### Features

* use Django user to authenticate ([8e11f94](https://gitlab.com/bubblehouse/termiverse/commit/8e11f9407bb87c918e6c92dcf8ebbaa2b32d42c7))

## [0.10.4](https://gitlab.com/bubblehouse/termiverse/compare/v0.10.3...v0.10.4) (2023-12-03)


### Bug Fixes

* raw id field ([a79710d](https://gitlab.com/bubblehouse/termiverse/commit/a79710de92b247f63705d7aed330daa326048363))

## [0.10.3](https://gitlab.com/bubblehouse/termiverse/compare/v0.10.2...v0.10.3) (2023-12-03)


### Bug Fixes

* raw id field ([5573c4e](https://gitlab.com/bubblehouse/termiverse/commit/5573c4efffaab10c77f4adf4ef03ad8cc3b2ec11))

## [0.10.2](https://gitlab.com/bubblehouse/termiverse/compare/v0.10.1...v0.10.2) (2023-12-03)


### Bug Fixes

* add Player model for User/Avatar integration ([02b8f68](https://gitlab.com/bubblehouse/termiverse/commit/02b8f6867266d184749aaa2df09f9d1af2ebb10b))
* add Player model for User/Avatar integration ([4554112](https://gitlab.com/bubblehouse/termiverse/commit/45541125224c2fe43915f07feea48f3f011ea626))

## [0.10.1](https://gitlab.com/bubblehouse/termiverse/compare/v0.10.0...v0.10.1) (2023-12-03)


### Bug Fixes

* bootstrapping issues, refactoring ([f24f4d3](https://gitlab.com/bubblehouse/termiverse/commit/f24f4d3aa6be6427d1a29a90cbbb97e455e6f932))

## [0.10.0](https://gitlab.com/bubblehouse/termiverse/compare/v0.9.0...v0.10.0) (2023-12-03)


### Features

* ownership and ACL support ([a1c96ca](https://gitlab.com/bubblehouse/termiverse/commit/a1c96ca82e55eb0a40a03c4a4909ef67593ad022))

## [0.9.0](https://gitlab.com/bubblehouse/termiverse/compare/v0.8.0...v0.9.0) (2023-12-03)


### Features

* replace temp shell with python repl ([ed75b0a](https://gitlab.com/bubblehouse/termiverse/commit/ed75b0ac1c5eb49f901c3af55e1fd0499e4983c8))

## [0.8.0](https://gitlab.com/bubblehouse/termiverse/compare/v0.7.0...v0.8.0) (2023-11-30)


### Features

* created db init script ([6436a54](https://gitlab.com/bubblehouse/termiverse/commit/6436a54df2628baed601cf8b875a1f1884992613))


### Bug Fixes

* continuing to address init issues ([05b7fa9](https://gitlab.com/bubblehouse/termiverse/commit/05b7fa9786215e8d16bef6d54e490b02496620e9))
* implementing more permissions details, refactoring ([f7534fc](https://gitlab.com/bubblehouse/termiverse/commit/f7534fca30242f4ab346b16747f1eeb880926acb))

## [0.7.0](https://gitlab.com/bubblehouse/termiverse/compare/v0.6.0...v0.7.0) (2023-11-27)


### Features

* begin implementing code execution ([ec1ad55](https://gitlab.com/bubblehouse/termiverse/commit/ec1ad55d3778a8ac4121db714401b0d158cb20fe))

## [0.6.0](https://gitlab.com/bubblehouse/termiverse/compare/v0.5.0...v0.6.0) (2023-11-14)


### Features

* created core app with model imported from antioch ([1cd61be](https://gitlab.com/bubblehouse/termiverse/commit/1cd61be9ef33e52c77d1088ff75403aa3d9c3d87))

## [0.5.0](https://gitlab.com/bubblehouse/termiverse/compare/v0.4.3...v0.5.0) (2023-11-04)


### Features

* fully interactive SSH prompt using `python-prompt-toolkit` ([d9e567d](https://gitlab.com/bubblehouse/termiverse/commit/d9e567d3674c93ad210c2fc6c1f412f4c07f6a7f))
* setup postgres settings for dev and local ([7361ccf](https://gitlab.com/bubblehouse/termiverse/commit/7361ccfff781b98f9c4c51e364217bd91e2e164f))


### Bug Fixes

* force release ([014d462](https://gitlab.com/bubblehouse/termiverse/commit/014d4620de1cf6eea0aebcfde2e65642a5401464))
* force release ([1e8641c](https://gitlab.com/bubblehouse/termiverse/commit/1e8641c39e250b3f9d7f6d35d1b0fcf5211559af))
* force release ([f3b4a8f](https://gitlab.com/bubblehouse/termiverse/commit/f3b4a8fb7b061802115480c48ed9b7491d50449f))
* force release ([6d296a1](https://gitlab.com/bubblehouse/termiverse/commit/6d296a1ed3a53ef78776ec4bb169188aa648e285))

## [0.4.3](https://gitlab.com/bubblehouse/termiverse/compare/v0.4.2...v0.4.3) (2023-10-10)


### Bug Fixes

* helm chart selector labels for shell service ([02beba3](https://gitlab.com/bubblehouse/termiverse/commit/02beba38f8e71f797884d56eb09c8bf448622656))

## [0.4.2](https://gitlab.com/bubblehouse/termiverse/compare/v0.4.1...v0.4.2) (2023-10-10)


### Bug Fixes

* use port name ([26b7379](https://gitlab.com/bubblehouse/termiverse/commit/26b73791b1a9c2fe4aabf240423eb5688c113a0e))

## [0.4.1](https://gitlab.com/bubblehouse/termiverse/compare/v0.4.0...v0.4.1) (2023-10-10)


### Bug Fixes

* port for shell service ([4d0df41](https://gitlab.com/bubblehouse/termiverse/commit/4d0df4146e895a9ebf5c343861766c01dd8a1a34))

## [0.4.0](https://gitlab.com/bubblehouse/termiverse/compare/v0.3.7...v0.4.0) (2023-09-30)


### Features

* add shell to compose file ([7704588](https://gitlab.com/bubblehouse/termiverse/commit/77045880128cc934bd912e6d5b8c7e0e1d6fc62d))


### Bug Fixes

* configure logging ([942743b](https://gitlab.com/bubblehouse/termiverse/commit/942743b6da1346e0de481624b8c9e69f58584245))
* dont try to install native python modules ([48a7a9c](https://gitlab.com/bubblehouse/termiverse/commit/48a7a9c4b9301d28bad97b6778ccc0d4823aaabb))
* use correct listening address ([1cbed76](https://gitlab.com/bubblehouse/termiverse/commit/1cbed76ac2e888ac29f674052facf1a686589642))

## [0.3.7](https://gitlab.com/bubblehouse/termiverse/compare/v0.3.6...v0.3.7) (2023-09-23)


### Bug Fixes

* installed uwsgi-python3 and net-tools ([7ded073](https://gitlab.com/bubblehouse/termiverse/commit/7ded073f9acb9e965bb98c7eeb9e6edf2c94d2ef))

## [0.3.6](https://gitlab.com/bubblehouse/termiverse/compare/v0.3.5...v0.3.6) (2023-09-19)


### Bug Fixes

* remove broken redirect ([fd38705](https://gitlab.com/bubblehouse/termiverse/commit/fd3870595ee758c17955ac9622c5794ec651a074))

## [0.3.5](https://gitlab.com/bubblehouse/termiverse/compare/v0.3.4...v0.3.5) (2023-09-19)


### Bug Fixes

* disable liveness/readiness for ssh server for now ([221434b](https://gitlab.com/bubblehouse/termiverse/commit/221434bb18b30432707feabbdee4b8ede2de6fb6))

## [0.3.4](https://gitlab.com/bubblehouse/termiverse/compare/v0.3.3...v0.3.4) (2023-09-19)


### Bug Fixes

* change ownership of server key ([cf23255](https://gitlab.com/bubblehouse/termiverse/commit/cf232550c426c054327a8cc4c55bb0f8a36b3c08))

## [0.3.3](https://gitlab.com/bubblehouse/termiverse/compare/v0.3.2...v0.3.3) (2023-09-19)


### Bug Fixes

* force release ([c977ec7](https://gitlab.com/bubblehouse/termiverse/commit/c977ec75a8f3aaaa927918844d97f02aebaac0cd))
* generate a key inside the Dockfile ([9bcf9e8](https://gitlab.com/bubblehouse/termiverse/commit/9bcf9e8646224cce521a0a5ff82974931a4b8e8a))
* generate a key inside the Dockfile ([a46d0cc](https://gitlab.com/bubblehouse/termiverse/commit/a46d0cc8fedb6b631eee8f58f5ea9edd2f686c29))
* install ssh ([e6e3f3f](https://gitlab.com/bubblehouse/termiverse/commit/e6e3f3f2951c630672c05bc2705ef684694d7021))
* mixed up service ports ([0376e5b](https://gitlab.com/bubblehouse/termiverse/commit/0376e5b424edb20e7b35a7085b0c6c58a3f48f77))

## [0.3.2](https://gitlab.com/bubblehouse/termiverse/compare/v0.3.1...v0.3.2) (2023-09-19)


### Bug Fixes

* chart typo ([00bcb1a](https://gitlab.com/bubblehouse/termiverse/commit/00bcb1a218c6353f31a36850fb41c9f29a5cf015))

## [0.3.1](https://gitlab.com/bubblehouse/termiverse/compare/v0.3.0...v0.3.1) (2023-09-19)


### Bug Fixes

* port updates ([4041617](https://gitlab.com/bubblehouse/termiverse/commit/4041617ea99f9e287ab95d429b9d337cdc3e9164))

## [0.3.0](https://gitlab.com/bubblehouse/termiverse/compare/v0.2.3...v0.3.0) (2023-09-18)


### Features

* implement a trivial SSH server as a Django Management command ([9291f50](https://gitlab.com/bubblehouse/termiverse/commit/9291f50ff55ad31c227b974ef42d94152bf278da))

## [0.2.3](https://gitlab.com/bubblehouse/termiverse/compare/v0.2.2...v0.2.3) (2023-09-17)


### Bug Fixes

* ingress port correction ([6af8a74](https://gitlab.com/bubblehouse/termiverse/commit/6af8a743b05b6febdce8ed5501c976839e93ccdc))

## [0.2.2](https://gitlab.com/bubblehouse/termiverse/compare/v0.2.1...v0.2.2) (2023-09-17)


### Bug Fixes

* chart typo ([53872e6](https://gitlab.com/bubblehouse/termiverse/commit/53872e673d68dcff7b57fd5fd2189529805ad559))
* force release ([f750eb3](https://gitlab.com/bubblehouse/termiverse/commit/f750eb3aaef3e1311af394676df3a908bc155c8b))

## [0.2.1](https://gitlab.com/bubblehouse/termiverse/compare/v0.2.0...v0.2.1) (2023-09-17)


### Bug Fixes

* more setup and Django settings refactoring ([47a0bac](https://gitlab.com/bubblehouse/termiverse/commit/47a0bacb129ca7047de78b9e748fd09de9ef0420))

## [0.2.0](https://gitlab.com/bubblehouse/termiverse/compare/v0.1.4...v0.2.0) (2023-09-17)


### Features

* added Rich library ([72787b5](https://gitlab.com/bubblehouse/termiverse/commit/72787b569d4d40b6655537af459e7dfb9d41f115))


### Bug Fixes

* disabled DBs and cache temporarily in dev, moved around environment names ([29462b6](https://gitlab.com/bubblehouse/termiverse/commit/29462b6778b1e17be8e8355ed50837c5d5d0ca93))

## [0.1.4](https://gitlab.com/bubblehouse/termiverse/compare/v0.1.3...v0.1.4) (2023-09-17)


### Bug Fixes

* chart semantic-release version missing files ([bbccce5](https://gitlab.com/bubblehouse/termiverse/commit/bbccce510cbb11a825b95253ee3ee62220732bb9))
* chart semantic-release version missing files ([579ca1a](https://gitlab.com/bubblehouse/termiverse/commit/579ca1a305716b0a97b88b6712e03514cf8e1b1c))

## [0.1.3](https://gitlab.com/bubblehouse/termiverse/compare/v0.1.2...v0.1.3) (2023-09-17)


### Bug Fixes

* chart semantic-release version ([42aeae4](https://gitlab.com/bubblehouse/termiverse/commit/42aeae49fa500b11333ecc2b9568429980916ebe))

## [0.1.2](https://gitlab.com/bubblehouse/termiverse/compare/v0.1.1...v0.1.2) (2023-09-17)


### Bug Fixes

* update chart image ([9bf0976](https://gitlab.com/bubblehouse/termiverse/commit/9bf0976ae25f28e194ccc5bb713733e5b1772551))

## [0.1.1](https://gitlab.com/bubblehouse/termiverse/compare/v0.1.0...v0.1.1) (2023-09-17)


### Bug Fixes

* avoid pinning Python version, include wheel as release attachment ([f83b300](https://gitlab.com/bubblehouse/termiverse/commit/f83b300be9968fb20c57412868d2c64c87c53b9f))
* force release ([153af17](https://gitlab.com/bubblehouse/termiverse/commit/153af17ebf97acd38fbac0c33ffe3c7afc8cf38d))
* start using base image ([21295d3](https://gitlab.com/bubblehouse/termiverse/commit/21295d3751382b4711e2c2a07d8b3c0fbc248ee9))
* use poetry publish ([d966ff4](https://gitlab.com/bubblehouse/termiverse/commit/d966ff4a2f3ccfc5b48f22009f520df7aa1cede8))
