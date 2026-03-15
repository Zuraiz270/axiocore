import { Injectable, OnModuleInit, Logger } from '@nestjs/common';
import * as Minio from 'minio';

@Injectable()
export class StorageService implements OnModuleInit {
  private readonly logger = new Logger(StorageService.name);
  private minioClient: Minio.Client;
  private readonly bucketName = process.env.MINIO_BUCKET || 'axiocore-documents';

  onModuleInit() {
    this.minioClient = new Minio.Client({
      endPoint: process.env.MINIO_ENDPOINT || 'localhost',
      port: parseInt(process.env.MINIO_PORT || '9000'),
      useSSL: process.env.MINIO_USE_SSL === 'true',
      accessKey: process.env.MINIO_ACCESS_KEY || 'admin',
      secretKey: process.env.MINIO_SECRET_KEY || 'password',
    });
    this.logger.log('MinIO Storage Service Initialized');
  }

  async listAllObjects(): Promise<string[]> {
    return new Promise((resolve, reject) => {
      const objectsList: string[] = [];
      const stream = this.minioClient.listObjectsV2(this.bucketName, '', true);
      
      stream.on('data', (obj) => {
        if (obj.name) objectsList.push(obj.name);
      });
      
      stream.on('error', (err) => {
        this.logger.error(`Error listing MinIO objects: ${err.message}`);
        reject(err);
      });
      
      stream.on('end', () => {
        resolve(objectsList);
      });
    });
  }

  async deleteObject(objectName: string): Promise<void> {
    await this.minioClient.removeObject(this.bucketName, objectName);
    this.logger.log(`Deleted object from MinIO: ${objectName}`);
  }

  async getObjectStat(objectName: string): Promise<Minio.BucketItemStat> {
    return this.minioClient.statObject(this.bucketName, objectName);
  }
}
