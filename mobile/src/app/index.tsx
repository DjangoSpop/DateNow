import { Redirect } from 'expo-router';

import { ROUTE_HREF } from '../navigation/bootRoute';
import { selectBootRoute, useAuthStore } from '../state/authStore';

/** Entry route: only ever redirects to the area the boot decision selected. */
export default function Index() {
  const route = useAuthStore(selectBootRoute);
  return <Redirect href={ROUTE_HREF[route]} />;
}
