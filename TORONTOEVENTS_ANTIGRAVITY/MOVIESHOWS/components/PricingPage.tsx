/**
 * UPDATE #102: Pricing Page Component
 * Display subscription plans
 */

import React from 'react';
import { subscriptionManager } from '../utils/subscriptionManager';

interface PricingPageProps {
    currentTier?: string;
    onSelectPlan: (planId: string) => void;
}

export function PricingPage({ currentTier, onSelectPlan }: PricingPageProps) {
    const plans = subscriptionManager.getPlans();

    return (
        <div className="pricing-page">
            <div className="pricing-header">
                <h1>Choose Your Plan</h1>
                <p>Select the perfect plan for your needs</p>
            </div>

            <div className="pricing-grid">
                {plans.map(plan => (
                    <div
                        key={plan.id}
                        className={`pricing-card ${currentTier === plan.tier ? 'current' : ''} ${plan.tier === 'premium' ? 'featured' : ''
                            }`}
                    >
                        {plan.tier === 'premium' && (
                            <div className="featured-badge">Most Popular</div>
                        )}

                        <div className="plan-header">
                            <h2>{plan.name}</h2>
                            <div className="plan-price">
                                {plan.price === 0 ? (
                                    <span className="price-free">Free</span>
                                ) : (
                                    <>
                                        <span className="price-amount">${plan.price}</span>
                                        <span className="price-interval">/{plan.interval}</span>
                                    </>
                                )}
                            </div>
                        </div>

                        <ul className="plan-features">
                            {plan.features.map((feature, index) => (
                                <li key={index}>
                                    <span className="check-icon">✓</span>
                                    {feature}
                                </li>
                            ))}
                        </ul>

                        <button
                            onClick={() => onSelectPlan(plan.id)}
                            className={`plan-button ${currentTier === plan.tier ? 'current' : ''}`}
                            disabled={currentTier === plan.tier}
                        >
                            {currentTier === plan.tier ? 'Current Plan' : 'Select Plan'}
                        </button>
                    </div>
                ))}
            </div>

            <div className="pricing-faq">
                <h3>Frequently Asked Questions</h3>

                <div className="faq-item">
                    <h4>Can I change my plan anytime?</h4>
                    <p>Yes! You can upgrade or downgrade your plan at any time.</p>
                </div>

                <div className="faq-item">
                    <h4>What payment methods do you accept?</h4>
                    <p>We accept all major credit cards, PayPal, and Apple Pay.</p>
                </div>

                <div className="faq-item">
                    <h4>Is there a free trial?</h4>
                    <p>Yes! All paid plans come with a 7-day free trial.</p>
                </div>
            </div>
        </div>
    );
}

const styles = `
.pricing-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 4rem 2rem;
}

.pricing-header {
  text-align: center;
  margin-bottom: 4rem;
}

.pricing-header h1 {
  font-size: 3rem;
  margin: 0 0 1rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.pricing-header p {
  font-size: 1.25rem;
  opacity: 0.8;
}

.pricing-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 2rem;
  margin-bottom: 4rem;
}

.pricing-card {
  position: relative;
  padding: 2rem;
  background: rgba(0, 0, 0, 0.3);
  border: 2px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  transition: all 0.3s;
}

.pricing-card:hover {
  transform: translateY(-8px);
  border-color: rgba(102, 126, 234, 0.5);
  box-shadow: 0 12px 24px rgba(102, 126, 234, 0.2);
}

.pricing-card.featured {
  border-color: #667eea;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
}

.pricing-card.current {
  border-color: #4ade80;
}

.featured-badge {
  position: absolute;
  top: -12px;
  left: 50%;
  transform: translateX(-50%);
  padding: 0.5rem 1.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 700;
  text-transform: uppercase;
}

.plan-header {
  text-align: center;
  margin-bottom: 2rem;
  padding-bottom: 2rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.plan-header h2 {
  margin: 0 0 1rem;
  font-size: 1.75rem;
}

.plan-price {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 0.25rem;
}

.price-free {
  font-size: 2rem;
  font-weight: 700;
  color: #4ade80;
}

.price-amount {
  font-size: 3rem;
  font-weight: 700;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.price-interval {
  font-size: 1.25rem;
  opacity: 0.6;
}

.plan-features {
  list-style: none;
  padding: 0;
  margin: 0 0 2rem;
}

.plan-features li {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.check-icon {
  color: #4ade80;
  font-weight: 700;
  font-size: 1.25rem;
}

.plan-button {
  width: 100%;
  padding: 1rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 8px;
  color: white;
  font-weight: 700;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s;
}

.plan-button:hover:not(:disabled) {
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.plan-button:disabled {
  background: rgba(255, 255, 255, 0.1);
  cursor: not-allowed;
}

.plan-button.current {
  background: #4ade80;
  color: #0a0a0a;
}

.pricing-faq {
  max-width: 800px;
  margin: 0 auto;
}

.pricing-faq h3 {
  text-align: center;
  font-size: 2rem;
  margin-bottom: 2rem;
}

.faq-item {
  margin-bottom: 2rem;
  padding: 1.5rem;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
}

.faq-item h4 {
  margin: 0 0 0.75rem;
  font-size: 1.25rem;
}

.faq-item p {
  margin: 0;
  opacity: 0.8;
  line-height: 1.6;
}

@media (max-width: 768px) {
  .pricing-grid {
    grid-template-columns: 1fr;
  }
}
`;
