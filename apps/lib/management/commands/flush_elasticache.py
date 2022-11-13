from django.core.management.base import BaseCommand

from project import settings

import boto.elasticache


class Command(BaseCommand):
    args = 'cluster_id'
    help = 'usage: python manage.py flush_elasticache <region> <list of clusers>'

    def handle(self, *args, **options):
        region_to_flush = args[0]
        aws_region = None

        regionList = boto.elasticache.regions()
        for region in regionList:
            if region.name == region_to_flush:
                aws_region = region
                break

        for myCluster in args:
            if myCluster == region_to_flush:
                continue

            clusterInfo = boto.elasticache.layer1.ElastiCacheConnection(
                region=aws_region,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            ).describe_cache_clusters(
                cache_cluster_id=myCluster,
                show_cache_node_info=True
            )
            nodes = clusterInfo['DescribeCacheClustersResponse']['DescribeCacheClustersResult']['CacheClusters'][0]['CacheNodes']

            nodeList = []
            for node in nodes:

                nodeList.append(node['CacheNodeId'])

            boto.elasticache.layer1.ElastiCacheConnection(
                region=aws_region,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            ).reboot_cache_cluster(myCluster, nodeList)
