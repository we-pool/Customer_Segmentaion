import math, random
from flask import Blueprint
from flask import (render_template, url_for, flash,
                   redirect, request, abort, Blueprint)
from flask_login import current_user, login_required
from flaskapp import db
from sqlalchemy import case
from flaskapp.models import Profile, Job, User
from flaskapp.profiles.forms import ProfileForm
from flaskapp.recommend.jobs_for_freelancers import results
from flaskapp.recommend.final_freelancers.bucketing import getFinalList
from flaskapp.segment.predict.for_new_profiles.results import predictSegment
from flaskapp.recommend.final_jobs.similar_freelancers import getSimilarFLs
from flaskapp.recommend.final_jobs.check_jobs_for_freelancers import getJobs
from flaskapp.data_updater import update_data as update_data

profiles = Blueprint('profiles', __name__)

dataUpdater = update_data.Data_Updater()

@profiles.route('/profile/new', methods=['GET', 'POST'])
@login_required
def new_profile():
    form = ProfileForm()
    if form.validate_on_submit():
        profile_cluster_id = predictSegment(form.min_starting_rate.data, form.max_starting_rate.data, form.min_hourly_rate.data, form.max_hourly_rate.data)
        skills = form.skills.data if isinstance(form.skills.data, list) else form.skills.data.split(', ')
        skills_list = []
        for skill in skills:
            skills_list.append(skill.capitalize())
        skills_list = str(skills_list)
        profile = Profile(location=form.location.data, skills=skills_list, min_starting_rate=form.min_starting_rate.data, max_starting_rate=form.max_starting_rate.data, min_hourly_rate=form.min_hourly_rate.data, max_hourly_rate=form.max_hourly_rate.data, profile_cluster_id=profile_cluster_id, user=current_user)
        db.session.add(profile)
        db.session.commit()
        profile = Profile.query.filter_by(id=profile.id).first_or_404()
        dataUpdater.add_profile(profile)
        print('Updated cluster id: ', profile_cluster_id)
        #dataUpdater.close_logs()
        flash('Your freelancer profile has been created!', 'success')
        return redirect(url_for('main.home'))
    return render_template('create_profile.html', title='Create New Freelancer Profile', form=form, legend='Create New Freelancer Profile', purpose='create')


@profiles.route('/freelancer_user/<string:userid>')
def profile_posts(userid):
    #page = request.args.get('page', 1, type=int)
    fluser = User.query.filter_by(id=userid).first_or_404()
    profiles = Profile.query.filter_by(user=fluser)\
                    .order_by(Profile.id.desc())
    #               .paginate(page=page, per_page=5)
  
    return render_template('profiles.html', profiles=profiles, user=fluser)


@profiles.route('/profile/<int:profile_id>', )
def profile(profile_id):
    profile = Profile.query.get_or_404(profile_id)

    #no of recommendations in the final listing 
    N = 30
    #no of recommendations per page
    n = 10

    #respective percentage/proportion of recommendation to be shown respectively from buckets of hired, invited and content-based freelancers
    pc_p_quoted = 0.4
    pc_quoted = 0.3
    pc_content = 0.3

    #print('Input Freelancer: ',profile.id, ', ',profile.user.username, ', ',profile.location)
    profile_cluster_id = profile.profile_cluster_id
    print('Profile_CLuster_Id from Route: ',profile_cluster_id)
    similar_fls = getSimilarFLs(profile_id, profile_cluster_id)
    similar_fls_unames = [Profile.query.filter_by(id=int(id)).first().user.username for id in similar_fls]
    #print(similar_fls_unames)
    jobs_p_quoted, jobs_quoted = getJobs(similar_fls_unames)
    jobs_content = results.getResults(profile_id, 10)
    
    jobs_tuple = (jobs_p_quoted, jobs_quoted, jobs_content)
    rec_jobs_ids = jobs_p_quoted + jobs_quoted + jobs_content
    print('Ids: ',rec_jobs_ids)
    ##############
    #include bucketing algo if required
    final_list = getFinalList(N, n, jobs_tuple, pc_p_quoted, pc_quoted, pc_content)

    '''
    pages = math.ceil(N/n)
    initial_list = rec_jobs_ids
    final_list = []
    for page in range(pages):
        temp = initial_list[:n]
        #print('              original: ',temp)
        random.shuffle(temp)
        #print('              Shuffled: ',temp)
        final_list = final_list + temp
        initial_list = initial_list[n:]
    '''
    print('Final Ids: ',final_list)
    ##############

    ordering = case(
        {id: index for index, id in enumerate(final_list)},
        value=Job.id
    )
    page = request.args.get('page', 1, type=int)
    rec_jobs = Job.query.filter(Job.id.in_(final_list)).order_by(ordering).paginate(page=page, per_page=n)

    return render_template('profile.html', id=profile.id, profile=profile, location=profile.location, skills=profile.skills, min_hourly_rate=profile.min_hourly_rate, rec_jobs=rec_jobs)


@profiles.route('/profile/<int:profile_id>/update', methods=['GET', 'POST'])
@login_required
def update_profile(profile_id):
    profile = Profile.query.get_or_404(profile_id)
    if profile.user != current_user:
        abort(403)
    form = ProfileForm()
    if form.validate_on_submit():
        profile.location = form.location.data
        skills = form.skills.data if isinstance(form.skills.data, list) else form.skills.data.split(', ')
        skills_list = []
        for skill in skills:
            skills_list.append(skill.capitalize())
        skills_list = str(skills_list)
        profile.skills = skills_list
        profile.min_hourly_rate = form.min_hourly_rate.data
        profile.max_hourly_rate = form.max_hourly_rate.data
        profile.min_starting_rate = form.min_starting_rate.data
        profile.max_starting_rate = form.max_starting_rate.data
        profile_cluster_id = predictSegment(form.min_starting_rate.data, form.max_starting_rate.data, form.min_hourly_rate.data, form.max_hourly_rate.data)
        profile.profile_cluster_id = profile_cluster_id
        db.session.commit()
        profile = Profile.query.get_or_404(profile_id)
        dataUpdater.update_profile(profile)
        print('Updated cluster id: ',profile_cluster_id)
        flash('Your freelancer profile has been updated', 'success')
        return redirect(url_for('profiles.profile', profile_id=profile.id))
    elif request.method == 'GET':
        form.location.data = profile.location
        form.skills.data = profile.skills
        form.min_hourly_rate.data = profile.min_hourly_rate
        form.max_hourly_rate.data = profile.max_hourly_rate
        form.min_starting_rate.data = profile.min_starting_rate
        form.max_starting_rate.data = profile.max_starting_rate
    return render_template('create_profile.html', title='Update Freelancer Profile', form=form, legend='Update Freelancer Profile', purpose='update')


@profiles.route('/profile/<int:profile_id>/delete', methods=['POST'])
@login_required
def delete_profile(profile_id):
    profile = Profile.query.get_or_404(profile_id)
    if profile.user != current_user:
        abort(403)
    db.session.delete(profile)
    db.session.commit()
    dataUpdater.delete_profile(profile)
    #dataUpdater.resetProfileIds()
    flash('The freelancer profile has been deleted', 'success')
    return redirect(url_for('main.home'))
