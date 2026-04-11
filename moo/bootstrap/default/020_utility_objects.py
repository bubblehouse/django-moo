# pylint: disable=undefined-variable
lock_utils, _ = bootstrap.get_or_create_object("Lock Utilities", unique_name=True)
sys.set_property("lock_utils", lock_utils)

string_utils, _ = bootstrap.get_or_create_object("String Utilities", unique_name=True)
sys.set_property("string_utils", string_utils)

match_utils, _ = bootstrap.get_or_create_object("Match Utilities", unique_name=True)
sys.set_property("match_utils", match_utils)

gender_utils, _ = bootstrap.get_or_create_object("Gender Utilities", unique_name=True)
sys.set_property("gender_utils", gender_utils)
gender_utils.set_property("pronouns", ["ps", "po", "pp", "pr", "pq", "psc", "poc", "ppc", "prc", "pqc"])
gender_utils.set_property("genders", ["neuter", "male", "female", "plural"])
gender_utils.set_property("ps", ["it", "he", "she", "they"])
gender_utils.set_property("po", ["it", "him", "her", "them"])
gender_utils.set_property("pp", ["its", "his", "her", "their"])
gender_utils.set_property("pr", ["itself", "himself", "herself", "themselves"])
gender_utils.set_property("pq", ["its", "his", "hers", "theirs"])
gender_utils.set_property("psc", ["It", "He", "She", "They"])
gender_utils.set_property("poc", ["It", "Him", "Her", "Them"])
gender_utils.set_property("ppc", ["Its", "His", "Hers", "Their"])
gender_utils.set_property("prc", ["Itself", "Himself", "Herself", "Themselves"])
gender_utils.set_property("pqc", ["Its", "His", "Hers", "Theirs"])
