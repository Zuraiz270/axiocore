import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { SecurityExceptionFilter } from './common/filters/security-exception.filter';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.useGlobalFilters(new SecurityExceptionFilter());
  await app.listen(process.env.PORT ?? 3001);
}
bootstrap();
