#!/usr/bin/env python3
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from decouple import config

def create_database():
    # 数据库连接参数
    db_name = config('DB_NAME', default='testdb')
    db_user = config('DB_USER', default='postgres')
    db_password = config('DB_PASSWORD', default='')
    db_host = config('DB_HOST', default='127.0.0.1')
    db_port = config('DB_PORT', default='5432')
    
    try:
        # 连接到PostgreSQL服务器（连接到默认的postgres数据库）
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database='postgres'  # 连接到默认数据库
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # 检查数据库是否已存在
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
        exists = cursor.fetchone()
        
        if not exists:
            # 创建数据库
            cursor.execute(f'CREATE DATABASE "{db_name}"')
            print(f"数据库 '{db_name}' 创建成功！")
        else:
            print(f"数据库 '{db_name}' 已存在。")
            
        cursor.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"创建数据库时出错: {e}")
        return False
    
    return True

if __name__ == "__main__":
    create_database()
