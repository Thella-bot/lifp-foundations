import os
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, Column, String, Float
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import time

DATABASE_URL = (
    f"postgresql://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
    f"@{os.environ['POSTGRES_HOST']}:5432/{os.environ['POSTGRES_DB']}"
)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
Base = declarative_base()

class Feature(Base):
    __tablename__ = 'features'
    user_id = Column(String, primary_key=True)
    total_trans = Column(Float)
    freq_per_week = Column(Float)
    days_since_last = Column(Float)
    active_months = Column(Float)
    cash_in = Column(Float)
    cash_out = Column(Float)
    net_cash_flow = Column(Float)
    ratio_out_in = Column(Float)
    avg_cash_in = Column(Float)
    avg_cash_out = Column(Float)
    std_amount = Column(Float)
    airtime_count = Column(Float)
    airtime_total = Column(Float)
    bill_count = Column(Float)
    bill_total = Column(Float)
    merchant_count = Column(Float)
    merchant_total = Column(Float)
    airtime_ratio = Column(Float)
    merchant_ratio = Column(Float)
    max_gap = Column(Float)
    median_gap = Column(Float)
    trend_slope = Column(Float)

def generate_synthetic_transactions(n_users=1000):
    np.random.seed(42)
    users = [f"USER_{i:04d}" for i in range(n_users)]
    start_date = pd.Timestamp('2024-01-01')
    end_date = pd.Timestamp('2024-12-31')
    good_users = users[:int(n_users * 0.7)]
    bad_users = users[int(n_users * 0.7):]

    rows = []
    for user in users:
        if user in good_users:
            n = np.random.randint(100, 200)
            types = ['cash_in','cash_out','airtime_purchase','bill_payment','merchant_payment']
        else:
            n = np.random.randint(50, 100)
            types = ['cash_in','cash_out','airtime_purchase']
        dates = pd.to_datetime(
            np.random.randint(
                start_date.value // 10**9,
                end_date.value // 10**9,
                n
            ), unit='s'
        )
        dates = sorted(dates)
        for ts in dates:
            month = ts.month
            if user in good_users:
                if month < 4:
                    w = [0.3, 0.3, 0.2, 0.1, 0.1]
                elif month < 8:
                    w = [0.3, 0.25, 0.15, 0.15, 0.15]
                else:
                    w = [0.25, 0.2, 0.15, 0.15, 0.25]
                tp = np.random.choice(types, p=w)
                if tp == 'cash_in':
                    amt = np.random.lognormal(4, 0.8)
                elif tp == 'cash_out':
                    amt = np.random.lognormal(3.5, 0.9)
                elif tp == 'airtime_purchase':
                    amt = np.random.uniform(5, 100)
                elif tp == 'bill_payment':
                    amt = np.random.uniform(50, 500)
                else:
                    amt = np.random.lognormal(3, 1)
            else:
                w = [0.3, 0.5, 0.2]
                tp = np.random.choice(types, p=w)
                if tp == 'cash_in':
                    amt = np.random.lognormal(4.5, 1.2)
                elif tp == 'cash_out':
                    amt = np.random.lognormal(4.5, 1.2)
                else:
                    amt = np.random.uniform(2, 50)
            rows.append([user, ts, tp, round(amt, 2)])
    df = pd.DataFrame(rows, columns=['user_id', 'timestamp', 'type', 'amount'])
    return df

def engineer_features(trans_df):
    trans_df['timestamp'] = pd.to_datetime(trans_df['timestamp'])
    features = []
    for user_id, grp in trans_df.groupby('user_id'):
        grp = grp.sort_values('timestamp')
        total_trans = len(grp)
        days_span = (grp['timestamp'].max() - grp['timestamp'].min()).days + 1
        freq_per_week = total_trans / (days_span / 7)
        days_since_last = (trans_df['timestamp'].max() - grp['timestamp'].max()).days
        active_months = grp['timestamp'].dt.month.nunique()
        cash_in = grp[grp['type']=='cash_in']['amount'].sum()
        cash_out = grp[grp['type']=='cash_out']['amount'].sum()
        net_cash_flow = cash_in - cash_out
        ratio_out_in = cash_out / (cash_in + 1e-9)
        avg_cash_in = grp[grp['type']=='cash_in']['amount'].mean() if len(grp[grp['type']=='cash_in'])>0 else 0
        avg_cash_out = grp[grp['type']=='cash_out']['amount'].mean() if len(grp[grp['type']=='cash_out'])>0 else 0
        std_amount = grp['amount'].std()
        airtime = grp[grp['type']=='airtime_purchase']
        airtime_count = len(airtime)
        airtime_total = airtime['amount'].sum()
        bill = grp[grp['type']=='bill_payment']
        bill_count = len(bill)
        bill_total = bill['amount'].sum()
        merchant = grp[grp['type']=='merchant_payment']
        merchant_count = len(merchant)
        merchant_total = merchant['amount'].sum()
        airtime_ratio = airtime_total / (cash_out + 1e-9)
        merchant_ratio = merchant_total / (cash_out + 1e-9)
        gaps = grp['timestamp'].diff().dt.days.dropna()
        max_gap = gaps.max() if not gaps.empty else 0
        median_gap = gaps.median() if not gaps.empty else 0
        monthly = grp.set_index('timestamp').resample('M')['amount'].sum()
        slope = 0.0
        if len(monthly) >= 3:
            x = np.arange(len(monthly))
            y = monthly.values
            slope = np.polyfit(x, y, 1)[0]
        features.append({
            'user_id': user_id,
            'total_trans': total_trans,
            'freq_per_week': freq_per_week,
            'days_since_last': days_since_last,
            'active_months': active_months,
            'cash_in': cash_in,
            'cash_out': cash_out,
            'net_cash_flow': net_cash_flow,
            'ratio_out_in': ratio_out_in,
            'avg_cash_in': avg_cash_in,
            'avg_cash_out': avg_cash_out,
            'std_amount': std_amount,
            'airtime_count': airtime_count,
            'airtime_total': airtime_total,
            'bill_count': bill_count,
            'bill_total': bill_total,
            'merchant_count': merchant_count,
            'merchant_total': merchant_total,
            'airtime_ratio': airtime_ratio,
            'merchant_ratio': merchant_ratio,
            'max_gap': max_gap,
            'median_gap': median_gap,
            'trend_slope': slope
        })
    return pd.DataFrame(features)

def main():
    print("Generating synthetic transactions...")
    trans_df = generate_synthetic_transactions(1000)
    print("Engineering features...")
    feat_df = engineer_features(trans_df)

    Base.metadata.create_all(engine)
    session = Session()
    session.query(Feature).delete()
    for _, row in feat_df.iterrows():
        feature = Feature(**row.to_dict())
        session.add(feature)
    session.commit()
    print(f"Inserted {len(feat_df)} feature records.")
    session.close()

if __name__ == '__main__':
    main()