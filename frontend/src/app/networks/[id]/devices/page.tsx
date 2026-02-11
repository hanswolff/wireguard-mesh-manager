import { redirect } from 'next/navigation';

type DevicesPageParams = { id?: string };

export default async function DevicesPage({
  params,
}: {
  params: DevicesPageParams | Promise<DevicesPageParams>;
}) {
  const resolvedParams = await Promise.resolve(params);
  const networkId = resolvedParams.id;

  if (!networkId) {
    redirect('/networks');
  }

  redirect(`/networks/${networkId}`);
}
