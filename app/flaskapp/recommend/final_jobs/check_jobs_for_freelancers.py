from flaskapp.data_reader import read_data as rd
dataReader = rd.Data_Reader()
jobs = dataReader.get_jobs()
freelancers = dataReader.get_profiles()


def getJobs(fl_names):
    matching_jobs_premium_quoted = []
    for fl in fl_names:
        jobs['X'] = jobs['Link_of_premium_quoters'].map(lambda x: (fl in str(x)))
        matching_jobs_premium_quoted += list(jobs.loc[jobs['X'] == True]['Id'])
        #print(list(jobs.loc[jobs['X'] == True]['Id']))
        jobs.drop(['X'], axis=1, inplace=True)

    matching_jobs_quoted = []
    for fl in fl_names:
        jobs['X'] = jobs['Link_of_quoters'].map(lambda x: (fl in str(x)))
        matching_jobs_quoted += list(jobs.loc[jobs['X'] == True]['Id'])
        jobs.drop(['X'], axis=1, inplace=True)

    return (matching_jobs_premium_quoted, matching_jobs_quoted)