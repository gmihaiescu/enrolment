import { asyncServiceCreator, asyncDummyCreator } from './asyncFactory';

// Create all required async services here
export function createAsyncs(isDevelopment = false) {
  const apiBase = `/api`;

  // Various configs used for API calls
  const withDataAndCSRF = { csrf: true, withData: true };
  const withCSRF = { csrf: true, withData: false };

  const asyncs = {
    application: {
      fetchApplications: asyncServiceCreator('GET', `${apiBase}/applications/`),
      fetchApplication: id => asyncServiceCreator('GET', `${apiBase}/applications/${id}`)(),
      submit: asyncServiceCreator('POST', `${apiBase}/applications/`, withDataAndCSRF),
    },
    auth: {
      daco: () =>
        asyncServiceCreator('GET', `${apiBase}/daco/`)().catch(error => {
          // If DACO 403 then return custom error message in promise rejection
          if (error.response.status === 403)
            return Promise.reject(
              new Error(`You need a DACO account to be able to use this Application. <br/>
                          For more information, Please go to <a href="https://icgc.org/daco" target="_blank">https://icgc.org/daco</a>`),
            );

          return Promise.reject(error);
        }),
      googleSuccess: asyncServiceCreator('POST', `${apiBase}/auth/google/`, withDataAndCSRF),
      adminLogin: data =>
        asyncServiceCreator('POST', `${apiBase}/auth/login/`, withDataAndCSRF)(
          data,
        ).catch(error => {
          if (error.response.data && error.response.data.non_field_errors)
            return Promise.reject('The Credentials Provided were not correct');

          return Promise.reject('Something went wrong. Please Try again.');
        }),
      logout: asyncServiceCreator('POST', `${apiBase}/auth/logout/`, withCSRF),
    },
    profile: {
      getUser: asyncServiceCreator('GET', `${apiBase}/auth/user`),
      getSocial: asyncServiceCreator('GET', `${apiBase}/auth/social`),
      userCheck: id => asyncServiceCreator('GET', `${apiBase}/request/user/check/${id}`)(),
    },
    project: {
      fetchProjects: asyncServiceCreator('GET', `${apiBase}/projects/`),
      fetchProject: id => asyncServiceCreator('GET', `${apiBase}/projects/${id}`)(),
      fetchProjectUsers: id => asyncServiceCreator('GET', `${apiBase}/projects/users/${id}`)(),
      submit: asyncServiceCreator('POST', `${apiBase}/projects/`, withDataAndCSRF),
      approve: asyncServiceCreator('PUT', `${apiBase}/projects/`, withDataAndCSRF),
      deny: asyncServiceCreator('PUT', `${apiBase}/projects/`, withDataAndCSRF),
    },
    user: {
      dacoAccess: email => asyncServiceCreator('GET', `${apiBase}/daco/${email}`)(),
      userRequest: asyncServiceCreator('POST', `${apiBase}/request/user/`, withDataAndCSRF),
      fetchUserRequests: asyncServiceCreator('GET', `${apiBase}/projects/users/`),
      approveUserRequests: asyncServiceCreator(
        'PUT',
        `${apiBase}/projects/users/`,
        withDataAndCSRF,
      ),
      denyUserRequests: asyncServiceCreator('PUT', `${apiBase}/projects/users/`, withDataAndCSRF),
    },
  };

  // If dummy async services are required in development override here
  if (isDevelopment) {
    return {
      ...asyncs,
      auth: {
        ...asyncs.auth,
        daco: profileObj =>
          asyncDummyCreator(
            {
              user: {
                openid: profileObj.email,
                csa: true,
                userinfo: [
                  {
                    uid: profileObj.email,
                    name: profileObj.name,
                    email: profileObj.email,
                  },
                ],
              },
            },
            250,
          ),
      },
    };
  }

  return asyncs;
}
