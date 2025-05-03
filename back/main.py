from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware  # Importe CORSMiddleware aqui
from pydantic import BaseModel
from datetime import date
from typing import Optional
import asyncpg
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Cria a aplicação FastAPI
app = FastAPI()

# Configuração CORS - agora CORSMiddleware está disponível
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # URL do frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Transaction(BaseModel):
    id: int | None = None
    description: str
    amount: float
    type: str  # 'income' ou 'expense'
    date: date
    category: str | None = None

# Pool de conexões global
pool = None

@app.on_event("startup")
async def startup():
    global pool
    pool = await asyncpg.create_pool(os.getenv("DATABASE_URL"))
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                description TEXT NOT NULL,
                amount DECIMAL(10, 2) NOT NULL,
                type VARCHAR(10) CHECK (type IN ('income', 'expense')),
                date DATE NOT NULL,
                category VARCHAR(50)
            )
        """)

@app.on_event("shutdown")
async def shutdown():
    if pool:
        await pool.close()

@app.post("/transactions/")
async def create_transaction(transaction: Transaction):
    async with pool.acquire() as conn:
        record = await conn.fetchrow(
            "INSERT INTO transactions (description, amount, type, date, category) "
            "VALUES ($1, $2, $3, $4, $5) RETURNING id, description, amount, type, date, category",
            transaction.description, transaction.amount, transaction.type, 
            transaction.date, transaction.category
        )
        return dict(record)

@app.get("/transactions/")
async def get_transactions(
    month: Optional[int] = Query(None, ge=1, le=12, description="Mês (1-12) para filtrar"),
    year: Optional[int] = Query(None, description="Ano para filtrar"),
    start_date: Optional[date] = Query(None, description="Data inicial (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Data final (YYYY-MM-DD)")
):
    async with pool.acquire() as conn:
        try:
            query = "SELECT * FROM transactions"
            params = []
            conditions = []
            
            if month and year:
                conditions.append("EXTRACT(MONTH FROM date) = $1 AND EXTRACT(YEAR FROM date) = $2")
                params.extend([month, year])
            elif year:
                conditions.append("EXTRACT(YEAR FROM date) = $1")
                params.append(year)
            
            if start_date and end_date:
                conditions.append(f"date BETWEEN ${len(params)+1} AND ${len(params)+2}")
                params.extend([start_date, end_date])
            elif start_date:
                conditions.append(f"date >= ${len(params)+1}")
                params.append(start_date)
            elif end_date:
                conditions.append(f"date <= ${len(params)+1}")
                params.append(end_date)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY date DESC"
            
            records = await conn.fetch(query, *params)
            return [dict(record) for record in records]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao buscar transações: {str(e)}")

@app.get("/summary/")
async def get_summary(
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None)
):
    async with pool.acquire() as conn:
        try:
            income_query = "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type = 'income'"
            expenses_query = "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type = 'expense'"
            params = []
            
            if month and year:
                income_query += " AND EXTRACT(MONTH FROM date) = $1 AND EXTRACT(YEAR FROM date) = $2"
                expenses_query += " AND EXTRACT(MONTH FROM date) = $1 AND EXTRACT(YEAR FROM date) = $2"
                params.extend([month, year])
            elif year:
                income_query += " AND EXTRACT(YEAR FROM date) = $1"
                expenses_query += " AND EXTRACT(YEAR FROM date) = $1"
                params.append(year)
            
            income = await conn.fetchval(income_query, *params)
            expenses = await conn.fetchval(expenses_query, *params)
            
            return {
                "total_income": income,
                "total_expenses": expenses,
                "balance": income - expenses
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao calcular resumo: {str(e)}")

@app.delete("/transactions/{transaction_id}")
async def delete_transaction(transaction_id: int):
    async with pool.acquire() as conn:
        try:
            result = await conn.execute("DELETE FROM transactions WHERE id = $1", transaction_id)
            if result == "DELETE 0":
                raise HTTPException(status_code=404, detail="Transação não encontrada")
            return {"message": "Transação excluída com sucesso"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao excluir transação: {str(e)}")