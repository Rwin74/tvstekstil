'use strict';
// Modern API keys belong in apikey. Authorization carries a user JWT,
// or a legacy JWT key; sb_publishable / sb_secret keys are not JWTs.
function keys(env){return{publicKey:env.SUPABASE_PUBLISHABLE_KEY||env.SUPABASE_ANON_KEY,secretKey:env.SUPABASE_SECRET_KEY||env.SUPABASE_SERVICE_ROLE_KEY};}
function headers(key,token){const result={apikey:key};const bearer=token||key;if(bearer&&(!bearer.startsWith('sb_')))result.Authorization='Bearer '+bearer;return result;}
module.exports={keys,headers};
