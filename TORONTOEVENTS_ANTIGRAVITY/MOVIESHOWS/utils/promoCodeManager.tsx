/**
 * UPDATE #106: Discount & Promo Codes System
 * Handle promotional codes and discounts
 */

type DiscountType = 'percentage' | 'fixed' | 'trial_extension';

interface PromoCode {
    code: string;
    type: DiscountType;
    value: number; // percentage (0-100) or fixed amount
    description?: string;
    validFrom: string;
    validUntil?: string;
    maxUses?: number;
    currentUses: number;
    applicableTiers?: string[];
    firstTimeOnly?: boolean;
    active: boolean;
}

class PromoCodeManager {
    private codes: Map<string, PromoCode> = new Map();

    /**
     * Create promo code
     */
    createCode(code: PromoCode): void {
        this.codes.set(code.code.toUpperCase(), code);
    }

    /**
     * Validate promo code
     */
    validateCode(code: string, userId?: number, tier?: string): {
        valid: boolean;
        error?: string;
        discount?: number;
    } {
        const promoCode = this.codes.get(code.toUpperCase());

        if (!promoCode) {
            return { valid: false, error: 'Invalid promo code' };
        }

        if (!promoCode.active) {
            return { valid: false, error: 'This promo code is no longer active' };
        }

        // Check date validity
        const now = new Date();
        const validFrom = new Date(promoCode.validFrom);

        if (now < validFrom) {
            return { valid: false, error: 'This promo code is not yet valid' };
        }

        if (promoCode.validUntil) {
            const validUntil = new Date(promoCode.validUntil);
            if (now > validUntil) {
                return { valid: false, error: 'This promo code has expired' };
            }
        }

        // Check usage limit
        if (promoCode.maxUses && promoCode.currentUses >= promoCode.maxUses) {
            return { valid: false, error: 'This promo code has reached its usage limit' };
        }

        // Check tier applicability
        if (tier && promoCode.applicableTiers && !promoCode.applicableTiers.includes(tier)) {
            return { valid: false, error: 'This promo code is not applicable to your selected plan' };
        }

        return {
            valid: true,
            discount: promoCode.value
        };
    }

    /**
     * Apply promo code
     */
    applyCode(code: string, amount: number): number {
        const promoCode = this.codes.get(code.toUpperCase());
        if (!promoCode) return amount;

        if (promoCode.type === 'percentage') {
            return amount * (1 - promoCode.value / 100);
        } else if (promoCode.type === 'fixed') {
            return Math.max(0, amount - promoCode.value);
        }

        return amount;
    }

    /**
     * Increment usage count
     */
    incrementUsage(code: string): void {
        const promoCode = this.codes.get(code.toUpperCase());
        if (promoCode) {
            promoCode.currentUses++;
        }
    }

    /**
     * Get all active codes (admin only)
     */
    getActiveCodes(): PromoCode[] {
        return Array.from(this.codes.values()).filter(code => code.active);
    }

    /**
     * Deactivate code
     */
    deactivateCode(code: string): void {
        const promoCode = this.codes.get(code.toUpperCase());
        if (promoCode) {
            promoCode.active = false;
        }
    }
}

export const promoCodeManager = new PromoCodeManager();

// Create some default promo codes
promoCodeManager.createCode({
    code: 'WELCOME20',
    type: 'percentage',
    value: 20,
    description: '20% off your first month',
    validFrom: '2024-01-01',
    firstTimeOnly: true,
    currentUses: 0,
    active: true
});

promoCodeManager.createCode({
    code: 'PREMIUM50',
    type: 'percentage',
    value: 50,
    description: '50% off Premium plan',
    validFrom: '2024-01-01',
    validUntil: '2024-12-31',
    applicableTiers: ['premium'],
    maxUses: 100,
    currentUses: 0,
    active: true
});

promoCodeManager.createCode({
    code: 'SAVE10',
    type: 'fixed',
    value: 10,
    description: '$10 off any plan',
    validFrom: '2024-01-01',
    currentUses: 0,
    active: true
});

/**
 * Promo code input component
 */
import React, { useState } from 'react';

interface PromoCodeInputProps {
    onApply: (code: string, discount: number) => void;
    tier?: string;
    userId?: number;
}

export function PromoCodeInput({ onApply, tier, userId }: PromoCodeInputProps) {
    const [code, setCode] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [applied, setApplied] = useState(false);

    const handleApply = () => {
        setError('');
        setSuccess('');

        const result = promoCodeManager.validateCode(code, userId, tier);

        if (result.valid && result.discount !== undefined) {
            setSuccess(`Promo code applied! ${result.discount}% discount`);
            setApplied(true);
            onApply(code, result.discount);
            promoCodeManager.incrementUsage(code);
        } else {
            setError(result.error || 'Invalid promo code');
        }
    };

    const handleRemove = () => {
        setCode('');
        setError('');
        setSuccess('');
        setApplied(false);
        onApply('', 0);
    };

    return (
        <div className="promo-code-input">
            <div className="input-group">
                <input
                    type="text"
                    value={code}
                    onChange={(e) => setCode(e.target.value.toUpperCase())}
                    placeholder="Enter promo code"
                    disabled={applied}
                    className="promo-input"
                />
                {!applied ? (
                    <button onClick={handleApply} disabled={!code} className="apply-button">
                        Apply
                    </button>
                ) : (
                    <button onClick={handleRemove} className="remove-button">
                        Remove
                    </button>
                )}
            </div>

            {error && <div className="promo-error">{error}</div>}
            {success && <div className="promo-success">✓ {success}</div>}
        </div>
    );
}

const styles = `
.promo-code-input {
  margin: 1.5rem 0;
}

.input-group {
  display: flex;
  gap: 0.5rem;
}

.promo-input {
  flex: 1;
  padding: 0.75rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: white;
  font-size: 1rem;
  text-transform: uppercase;
}

.promo-input:focus {
  outline: none;
  border-color: #667eea;
}

.promo-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.apply-button,
.remove-button {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.apply-button {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.apply-button:hover:not(:disabled) {
  transform: scale(1.05);
}

.apply-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.remove-button {
  background: rgba(248, 113, 113, 0.2);
  color: #f87171;
}

.remove-button:hover {
  background: rgba(248, 113, 113, 0.3);
}

.promo-error {
  margin-top: 0.5rem;
  padding: 0.75rem;
  background: rgba(248, 113, 113, 0.1);
  border: 1px solid rgba(248, 113, 113, 0.3);
  border-radius: 6px;
  color: #f87171;
  font-size: 0.9rem;
}

.promo-success {
  margin-top: 0.5rem;
  padding: 0.75rem;
  background: rgba(74, 222, 128, 0.1);
  border: 1px solid rgba(74, 222, 128, 0.3);
  border-radius: 6px;
  color: #4ade80;
  font-size: 0.9rem;
}
`;
