// case49: 线程安全类测试
// 测试线程安全类的实现

class ThreadSafeCounter {
    private var count: Int64 = 0
    private let mutex = Mutex()
    
    public func increment() {
        mutex.lock()
        count = count + 1
        mutex.unlock()
    }
    
    public func getCount(): Int64 {
        mutex.lock()
        let value = count
        mutex.unlock()
        return value
    }
}

main() {
    let counter = ThreadSafeCounter()
    
    spawn {
        counter.increment()
    }
    
    spawn {
        counter.increment()
    }
}