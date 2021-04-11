import json, mysql.connector, csv
from github import Github
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
class Config():
	def __init__(self):
		try:
			with open("config.json", "r") as configFile:
				config = json.load(configFile)
				self.github_token = config["github_pat"]
				self.db_host = config["db_config"]["host"]
				self.db_user = config["db_config"]["username"]
				self.db_pass = config["db_config"]["password"]
				self.db_database = config["db_config"]["database"]
				self.testing = config["testing"]
		except FileNotFoundError:
			log("config.json does not exist. Please setup config from config.json.example", "ERROR")
			log("Exiting", "ERROR")
			exit()
		except KeyError:
			log("config.json is not valid. Please setup config from config.json.example", "ERROR")
			log("Exiting", "ERROR")
			exit()

class Codebase():
	def __init__(self):
		self.name = None
		self.repo_id = None
		self.storage_used = None
		self.readable_storage = None
		self.in_use = True

def log(text, type="INFO"):
	timestamp = str(datetime.now().utcnow()).split(".")[0]
	print("[{}] [{}] {}".format(timestamp, type, text))

def bytes2mb(size):
	return "{} MB".format(round(size/(1024*1024), 2))

log("Starting up...")
cfg = Config()
log("Config loaded")

codebases = []

if cfg.testing:
	log("RUNNING IN TESTING MODE", "WARNING")
	# TEMP LOAD OF CSV DATA
	with open("testing_data.csv") as csvfile:
		reader = csv.reader(csvfile)
		for row in reader:
			cb = Codebase()
			cb.repo_id = int(row[0])
			cb.storage_used = int(row[1])
			cb.name = row[2]
			codebases.append(cb)

else:
	# The regular load

	log("Getting repository list...")
	# Connect to DB
	dbcon = mysql.connector.connect(
		host=cfg.db_host,
		user=cfg.db_user,
		passwd=cfg.db_pass,
		db=cfg.db_database
	)
	cur = dbcon.cursor()

	# Pull
	cur.execute("SELECT Id FROM InstallationRepositories")
	ids = cur.fetchall()
	log("Found {} codebases to inspect".format(len(ids)))
	log("Calculating codebase size usage. This will take a while...")
	for id in ids:
		clean_id = id[0]
		cb = Codebase()
		cb.repo_id = clean_id
		cb.storage_used = 0

		cur.execute("SELECT SUM(OCTET_LENGTH(DATA)) FROM Images WHERE Id IN (SELECT BeforeImageId FROM MapDiffs WHERE InstallationRepositoryId=%s)", (clean_id,))
		value = cur.fetchone()[0]
		if value is not None:
			cb.storage_used += int(value)

		# Get afters
		cur.execute("SELECT SUM(OCTET_LENGTH(DATA)) FROM Images WHERE Id IN (SELECT AfterImageId FROM MapDiffs WHERE InstallationRepositoryId=%s)", (clean_id,))
		value = cur.fetchone()[0]
		if value is not None:
			cb.storage_used += int(value)

		# Get diffs
		cur.execute("SELECT SUM(OCTET_LENGTH(DATA)) FROM Images WHERE Id IN (SELECT DifferenceImageId FROM MapDiffs WHERE InstallationRepositoryId=%s)", (clean_id,))
		value = cur.fetchone()[0]
		if value is not None:
			cb.storage_used += int(value)

		if cb.storage_used > 0:
			codebases.append(cb)

	# Sort them out
	codebases.sort(key=lambda x: x.storage_used, reverse=True)

	log("Calculated size usage of {} codebases".format(len(codebases)))


	cur.close()
	dbcon.close()

	log("Pulling repo names for {} repos...".format(len(codebases)))

	git = Github(cfg.github_token)
	for codebase in codebases:
		try:
			repo = git.get_repo(codebase.repo_id)
			codebase.name =  repo.owner.login + "\\" + repo.name
		except Exception:
			log("Erorr processing repo {}. Removing...".format(codebase.repo_id), "ERROR")
			codebase.in_use = False

	log("Repo names retrieved for {} repos".format(len(codebases)))


# And back to normal
log("Formatting filesizes...")
for codebase in codebases:
	if codebase.in_use == False:
		continue
	# Remove codebases with <500mb storage used
	# Using remove here does weird things. Dont try change this.
	if codebase.storage_used < (500 * (1024 * 1024)) or codebase.storage_used is None:
		codebase.in_use = False
		continue

	codebase.readable_storage = bytes2mb(codebase.storage_used)
log("Done")

log("Genearting chart...")

labels = []
sizes = []

for codebase in codebases:
	if codebase.in_use == False:
		continue
	labels.append("{} ({})".format(codebase.name, codebase.readable_storage))
	sizes.append(codebase.storage_used)

# I dont know what half of this means
fig, ax = plt.subplots()
fig.set_size_inches(20, 15)
wedges, text = ax.pie(sizes, labels=labels, shadow=False, startangle=90)
ax.axis('equal')

timestamp = str(datetime.now().utcnow()).split(".")[0]
plt.title('MapDiffBot codebase data usage as of {}\nCodebases with < 500MB storage used are not displayed'.format(timestamp), fontdict={"fontsize": 40}, pad=45)
plt.savefig("output.png", dpi=200)
log("Complete!")
