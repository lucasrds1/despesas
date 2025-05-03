# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import date
from typing import List
import asyncpg
import os

app = FastAPI()

# Configuração do banco de dados
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/finance_db")

# Modelos Pydantic
class Transaction(BaseModel):
    id: int = None
    description: str
    amount: float
    type: str  # 'income' ou 'expense'
    date: date
    category: str = None

class TransactionCreate(BaseModel):
    description: str
    amount: float
    type: str
    date: date
    category: str = None

# Conexão com o banco de dados
async def get_connection():
    return await asyncpg.connect(DATABASE_URL)

# Criar tabela (executar uma vez)
@app.on_event("startup")
async def startup():
    conn = await get_connection()
    await conn.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            description TEXT NOT NULL,
            amount DECIMAL(10, 2) NOT NULL,
            type VARCHAR(10) CHECK (type IN ('income', 'expense')),
            date DATE NOT NULL,
            category VARCHAR(50)
        )
    ''')
    await conn.close()

# Rotas da API
@app.post("/transactions/", response_model=Transaction)
async def create_transaction(transaction: TransactionCreate):
    conn = await get_connection()
    try:
        record = await conn.fetchrow('''
            INSERT INTO transactions (description, amount, type, date, category)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, description, amount, type, date, category
        ''', transaction.description, transaction.amount, 
            transaction.type, transaction.date, transaction.category)
        return dict(record)
    finally:
        await conn.close()

@app.get("/transactions/", response_model=List[Transaction])
async def read_transactions():
    conn = await get_connection()
    try:
        records = await conn.fetch('SELECT * FROM transactions ORDER BY date DESC')
        return [dict(record) for record in records]
    finally:
        await conn.close()

@app.put("/transactions/{transaction_id}", response_model=Transaction)
async def update_transaction(transaction_id: int, transaction: TransactionCreate):
    conn = await get_connection()
    try:
        record = await conn.fetchrow('''
            UPDATE transactions
            SET description = $1, amount = $2, type = $3, date = $4, category = $5
            WHERE id = $6
            RETURNING id, description, amount, type, date, category
        ''', transaction.description, transaction.amount, 
            transaction.type, transaction.date, transaction.category, transaction_id)
        if not record:
            raise HTTPException(status_code=404, detail="Transaction not found")
        return dict(record)
    finally:
        await conn.close()

@app.delete("/transactions/{transaction_id}")
async def delete_transaction(transaction_id: int):
    conn = await get_connection()
    try:
        result = await conn.execute('DELETE FROM transactions WHERE id = $1', transaction_id)
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Transaction not found")
        return {"message": "Transaction deleted successfully"}
    finally:
        await conn.close()

@app.get("/transactions/summary/")
async def get_summary():
    conn = await get_connection()
    try:
        income = await conn.fetchval("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type = 'income'")
        expenses = await conn.fetchval("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type = 'expense'")
        balance = income - expenses
        return {
            "total_income": income,
            "total_expenses": expenses,
            "balance": balance
        }
    finally:
        await conn.close()