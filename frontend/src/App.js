import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [transactions, setTransactions] = useState([]);
  const [form, setForm] = useState({
    description: '',
    amount: '',
    type: 'expense',
    date: new Date().toISOString().split('T')[0],
    category: ''
  });
  const [summary, setSummary] = useState({ total_income: 0, total_expenses: 0, balance: 0 });
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());

  const fetchData = async () => {
    try {
      const [transRes, summaryRes] = await Promise.all([
        axios.get(`http://localhost:8000/transactions/?month=${selectedMonth}&year=${selectedYear}`),
        axios.get(`http://localhost:8000/summary/?month=${selectedMonth}&year=${selectedYear}`)
      ]);
      setTransactions(transRes.data);
      setSummary(summaryRes.data);
    } catch (error) {
      console.error("Erro ao buscar dados:", error);
    }
  };

  useEffect(() => {
    fetchData();
  }, [selectedMonth, selectedYear]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post('http://localhost:8000/transactions/', form);
      setForm({ ...form, description: '', amount: '' });
      fetchData();
    } catch (error) {
      console.error("Erro ao adicionar transação:", error);
      alert("Falha ao adicionar transação.");
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Tem certeza que deseja excluir esta transação?")) return;

    try {
      await axios.delete(`http://localhost:8000/transactions/${id}`);
      fetchData();
    } catch (error) {
      console.error("Erro ao excluir:", error);
      alert("Falha ao excluir transação.");
    }
  };

  const months = [
    { value: 1, label: 'Janeiro' },
    { value: 2, label: 'Fevereiro' },
    { value: 3, label: 'Março' },
    { value: 4, label: 'Abril' },
    { value: 5, label: 'Maio' },
    { value: 6, label: 'Junho' },
    { value: 7, label: 'Julho' },
    { value: 8, label: 'Agosto' },
    { value: 9, label: 'Setembro' },
    { value: 10, label: 'Outubro' },
    { value: 11, label: 'Novembro' },
    { value: 12, label: 'Dezembro' }
  ];

  // Gerar anos (dos últimos 5 anos até o próximo ano)
  const currentYear = new Date().getFullYear();
  const years = Array.from({ length: 7 }, (_, i) => currentYear - 3 + i);

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Controle Financeiro</h1>
      </header>

      {/* Filtro por Mês/Ano */}
      <div className="filter-container">
        <div className="filter-group">
          <label htmlFor="month">Mês:</label>
          <select
            id="month"
            value={selectedMonth}
            onChange={(e) => setSelectedMonth(parseInt(e.target.value))}
          >
            {months.map(month => (
              <option key={month.value} value={month.value}>{month.label}</option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label htmlFor="year">Ano:</label>
          <select
            id="year"
            value={selectedYear}
            onChange={(e) => setSelectedYear(parseInt(e.target.value))}
          >
            {years.map(year => (
              <option key={year} value={year}>{year}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="summary-container">
        <div className="summary-card balance">
          <h3>Saldo</h3>
          <p>R$ {summary.balance.toFixed(2)}</p>
        </div>
        <div className="summary-card income">
          <h3>Receitas</h3>
          <p>R$ {summary.total_income.toFixed(2)}</p>
        </div>
        <div className="summary-card expense">
          <h3>Despesas</h3>
          <p>R$ {summary.total_expenses.toFixed(2)}</p>
        </div>
      </div>

      <div className="form-container">
        <h2>Adicionar Transação</h2>
        <form onSubmit={handleSubmit} className="transaction-form">
          <div className="form-group">
            <input
              type="text"
              placeholder="Descrição"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              required
            />
          </div>

          <div className="form-group">
            <input
              type="number"
              placeholder="Valor"
              value={form.amount}
              onChange={(e) => setForm({ ...form, amount: parseFloat(e.target.value) || 0 })}
              step="0.01"
              min="0"
              required
            />
          </div>

          <div className="form-group">
            <select
              value={form.type}
              onChange={(e) => setForm({ ...form, type: e.target.value })}
            >
              <option value="income">Receita</option>
              <option value="expense">Despesa</option>
            </select>
          </div>

          <div className="form-group">
            <input
              type="date"
              value={form.date}
              onChange={(e) => setForm({ ...form, date: e.target.value })}
              required
            />
          </div>

          <button type="submit" className="submit-btn">
            Adicionar
          </button>
        </form>
      </div>

      <div className="transactions-container">
        <h2>Histórico de Transações</h2>
        <ul className="transactions-list">
          {transactions.map((t) => (
            <li key={t.id} className={`transaction-item ${t.type}`}>
              <div className="transaction-info">
                <span className="description">{t.description}</span>
                <span className="date">
                  {new Date(t.date).toLocaleDateString('pt-BR')}
                </span>
                <span className="amount">R$ {t.amount.toFixed(2)}</span>
              </div>
              <button
                onClick={() => handleDelete(t.id)}
                className="delete-btn"
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default App;